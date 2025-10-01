import sys
import os
import glob
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QFileDialog, QListWidget,
                             QListWidgetItem, QLabel, QComboBox, QLineEdit,
                             QGroupBox, QFormLayout, QSpinBox,
                             QColorDialog, QMessageBox, QSplitter)
from PyQt5.QtGui import QPixmap, QImage, QFont, QColor, QIcon, QPainter, QFontMetrics
from PyQt5.QtCore import Qt, QSize, QPoint
from PIL import Image, ImageDraw, ImageFont
import math

# ----------------------
# 可拖拽且直接绘制水印的预览 QLabel
# ----------------------
class WatermarkPreviewLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.base_pixmap = None  # 原始 QPixmap（full-size）
        self.display_pixmap = None  # 缩放后的显示 QPixmap（绘制使用）
        self.img_width = 0
        self.img_height = 0

        # watermark preview params
        self.text = "Watermark"
        self.font_size = 32
        self.color = QColor(0, 0, 0)
        self.opacity = 50  # percent
        self.position_text = "右下角"  # 预设位置名称或 "手动"

        # custom position stored in original image pixel coordinates (x, y) - center anchor
        self.custom_pos = None  # (x_pixels, y_pixels)

        # dragging state
        self.dragging = False
        self.drag_offset = QPoint(0, 0)  # offset between mouse and center when start drag

        # cache last computed draw bbox (in display coords) to detect clicks on watermark
        self.last_text_rect = None  # QRect in display coords

    def set_image(self, pixmap: QPixmap):
        """设置当前基准图片（原始大小）"""
        if pixmap is None or pixmap.isNull():
            self.base_pixmap = None
            self.display_pixmap = None
            self.img_width = 0
            self.img_height = 0
            self.update()
            return

        self.base_pixmap = pixmap
        self.img_width = pixmap.width()
        self.img_height = pixmap.height()
        self.update_display_pixmap()
        self.update()

    def update_preview_params(self, text=None, font_size=None, color=None, opacity=None, position_text=None):
        """更新水印参数（调用后会重绘）"""
        if text is not None:
            self.text = text if text.strip() else "Watermark"
        if font_size is not None:
            self.font_size = int(font_size)
        if color is not None:
            self.color = color
        if opacity is not None:
            self.opacity = int(opacity)
        if position_text is not None:
            self.position_text = position_text
        # If position becomes preset (非手动) we don't erase custom_pos; custom_pos only used if position_text == "手动"
        self.update_display_pixmap()
        self.update()

    def sizeHint(self):
        return QSize(400, 300)

    def update_display_pixmap(self):
        """生成适合当前 widget 大小的 display_pixmap（保持纵横比）"""
        if not self.base_pixmap:
            self.display_pixmap = None
            return
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            self.display_pixmap = self.base_pixmap
            return
        self.display_pixmap = self.base_pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)

        if not self.display_pixmap:
            # 显示提示文字
            painter.drawText(self.rect(), Qt.AlignCenter, "请选择一张图片")
            return

        # 计算 display_pixmap 放置在 widget 中的位置（居中）
        dp = self.display_pixmap
        dw = dp.width()
        dh = dp.height()
        x = (self.width() - dw) // 2
        y = (self.height() - dh) // 2

        # 画图片
        painter.drawPixmap(x, y, dp)

        # 计算缩放系数（image_pixel -> display_pixel）
        scale_x = dw / self.img_width if self.img_width else 1.0
        scale_y = dh / self.img_height if self.img_height else 1.0
        # 保持比例（一致）
        scale = min(scale_x, scale_y) if (self.img_width and self.img_height) else 1.0

        # 准备字体
        qfont = QFont()
        qfont.setPointSize(self.font_size)
        painter.setFont(qfont)
        fm = QFontMetrics(qfont)
        text = self.text
        text_w = fm.horizontalAdvance(text)
        text_h = fm.height()

        # 计算文本在 display 坐标系中的位置（左上角）
        margin = 10
        pos_name = self.position_text

        if pos_name == "手动" and self.custom_pos is not None:
            # custom_pos stored in original image pixels (center anchor)
            cx_img, cy_img = self.custom_pos
            disp_cx = int(cx_img * scale) + x
            disp_cy = int(cy_img * scale) + y
            # 将中心点映射到左上角
            tx = disp_cx - text_w // 2
            ty = disp_cy - text_h // 2
        else:
            # 预设九宫格位置
            # 左上, 上中, 右上, 左中, 居中, 右中, 左下, 下中, 右下
            if pos_name == "左上角":
                tx = x + margin
                ty = y + margin
            elif pos_name == "上中":
                tx = x + (dw - text_w) // 2
                ty = y + margin
            elif pos_name == "右上角":
                tx = x + dw - text_w - margin
                ty = y + margin
            elif pos_name == "左中":
                tx = x + margin
                ty = y + (dh - text_h) // 2
            elif pos_name == "居中":
                tx = x + (dw - text_w) // 2
                ty = y + (dh - text_h) // 2
            elif pos_name == "右中":
                tx = x + dw - text_w - margin
                ty = y + (dh - text_h) // 2
            elif pos_name == "左下角":
                tx = x + margin
                ty = y + dh - text_h - margin
            elif pos_name == "下中":
                tx = x + (dw - text_w) // 2
                ty = y + dh - text_h - margin
            elif pos_name == "右下角":
                tx = x + dw - text_w - margin
                ty = y + dh - text_h - margin
            else:
                # fallback to bottom-right
                tx = x + dw - text_w - margin
                ty = y + dh - text_h - margin

        # 记录文本矩形（display coords）以便点击检测
        from PyQt5.QtCore import QRect
        self.last_text_rect = QRect(tx, ty, text_w, text_h)

        # 设置颜色与透明度
        color = QColor(self.color)
        alpha = max(0, min(255, int(255 * (self.opacity / 100.0))))
        color.setAlpha(alpha)
        painter.setPen(color)

        # 直接绘制文本（未使用阴影）
        painter.drawText(tx, ty + fm.ascent(), text)  # y + ascent 以保证基线对齐

        painter.end()

    # ---------- 鼠标事件：实现拖拽（以文本中心为锚点） ----------
    def mousePressEvent(self, event):
        if not self.display_pixmap:
            return super().mousePressEvent(event)

        if event.button() == Qt.LeftButton:
            pt = event.pos()
            # 点击落在水印文本矩形内则允许拖拽
            if self.last_text_rect and self.last_text_rect.contains(pt):
                self.dragging = True
                # 记录拖拽偏移（mouse 与文本中心）
                center = self.last_text_rect.center()
                self.drag_offset = pt - center
                # 启动拖拽（为了立即开始移动）
                event.accept()
            else:
                super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging and self.display_pixmap:
            pt = event.pos()
            # 计算文本中心新的 display 坐标（mouse - offset）
            center_disp_x = pt.x() - self.drag_offset.x()
            center_disp_y = pt.y() - self.drag_offset.y()

            # 计算 display image origin (x,y) 与 scale （与 paintEvent 保持一致）
            dp = self.display_pixmap
            dw = dp.width()
            dh = dp.height()
            img_x = (self.width() - dw) // 2
            img_y = (self.height() - dh) // 2
            scale = dw / self.img_width if self.img_width else 1.0

            # 将 display 中的中心点映射回原始图像像素坐标
            cx_img = (center_disp_x - img_x) / scale
            cy_img = (center_disp_y - img_y) / scale

            # 限制到图片内
            cx_img = max(0, min(self.img_width, cx_img))
            cy_img = max(0, min(self.img_height, cy_img))

            self.custom_pos = (cx_img, cy_img)

            # 一旦用户拖拽，则视作“手动”模式（外部逻辑会把下拉框切换为“手动”）
            # 只是本控件内部不负责更改下拉框，主窗口会监听 custom_pos 变化（通过回调）
            self.update()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def clear_custom_pos(self):
        self.custom_pos = None
        self.update()

    def get_custom_pos_image_coords(self):
        """返回 custom_pos（原图像像素坐标）或 None"""
        return self.custom_pos

# ----------------------
# 主窗口
# ----------------------
class PhotoWatermarkApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

        # 存储导入的图片路径
        self.image_paths = []

        # 允许拖拽外部 file 到窗口
        self.setAcceptDrops(True)

    def initUI(self):
        self.setWindowTitle('Photo Watermark 2')
        self.setGeometry(100, 100, 1000, 640)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        splitter = QSplitter(Qt.Horizontal)

        # 左侧：图片列表与导入按钮
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        import_layout = QHBoxLayout()

        self.import_single_btn = QPushButton("导入单张图片")
        self.import_single_btn.clicked.connect(self.import_single_image)
        import_layout.addWidget(self.import_single_btn)

        self.import_multi_btn = QPushButton("导入多张图片")
        self.import_multi_btn.clicked.connect(self.import_multiple_images)
        import_layout.addWidget(self.import_multi_btn)

        self.import_folder_btn = QPushButton("导入文件夹")
        self.import_folder_btn.clicked.connect(self.import_folder)
        import_layout.addWidget(self.import_folder_btn)

        left_layout.addLayout(import_layout)

        self.image_list = QListWidget()
        self.image_list.setViewMode(QListWidget.IconMode)
        self.image_list.setIconSize(QSize(128, 128))
        self.image_list.setResizeMode(QListWidget.Adjust)
        self.image_list.setSpacing(10)
        left_layout.addWidget(self.image_list)

        self.remove_btn = QPushButton("移除选中图片")
        self.remove_btn.clicked.connect(self.remove_selected)
        left_layout.addWidget(self.remove_btn)

        splitter.addWidget(left_panel)

        # 右侧：预览 + 设置
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        preview_group = QGroupBox("预览")
        preview_layout = QVBoxLayout(preview_group)

        # 使用自定义的 WatermarkPreviewLabel
        self.preview_label = WatermarkPreviewLabel()
        self.preview_label.setMinimumHeight(360)
        self.preview_label.setStyleSheet("border: 1px solid #ccc; background: #fff;")
        preview_layout.addWidget(self.preview_label)
        right_layout.addWidget(preview_group)

        watermark_group = QGroupBox("水印设置")
        watermark_layout = QFormLayout(watermark_group)

        self.watermark_text = QLineEdit("Watermark")
        self.watermark_text.textChanged.connect(self.on_setting_changed)
        watermark_layout.addRow("水印文本:", self.watermark_text)

        self.font_size = QSpinBox()
        self.font_size.setRange(8, 200)
        self.font_size.setValue(32)
        self.font_size.valueChanged.connect(self.on_setting_changed)
        watermark_layout.addRow("字体大小:", self.font_size)

        self.opacity = QSpinBox()
        self.opacity.setRange(0, 100)
        self.opacity.setValue(50)
        self.opacity.valueChanged.connect(self.on_setting_changed)
        watermark_layout.addRow("透明度 (%):", self.opacity)

        color_layout = QHBoxLayout()
        self.color_btn = QPushButton("选择颜色")
        self.color_btn.setStyleSheet("background-color: black; color: white;")
        self.color_btn.clicked.connect(self.choose_color)
        self.watermark_color = QColor(0, 0, 0)
        color_layout.addWidget(self.color_btn)
        watermark_layout.addRow("水印颜色:", color_layout)

        self.position = QComboBox()
        # 添加九宫格 + 手动
        self.position.addItems(["左上角", "上中", "右上角", "左中", "居中", "右中", "左下角", "下中", "右下角", "手动"])
        self.position.currentIndexChanged.connect(self.on_position_changed)
        watermark_layout.addRow("水印位置:", self.position)

        right_layout.addWidget(watermark_group)

        output_group = QGroupBox("输出设置")
        output_layout = QFormLayout(output_group)

        output_folder_layout = QHBoxLayout()
        self.output_folder = QLineEdit()
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.choose_output_folder)
        output_folder_layout.addWidget(self.output_folder)
        output_folder_layout.addWidget(self.browse_btn)
        output_layout.addRow("输出文件夹:", output_folder_layout)

        self.output_format = QComboBox()
        self.output_format.addItems(["JPEG", "PNG"])
        output_layout.addRow("输出格式:", self.output_format)

        self.naming_rule = QComboBox()
        self.naming_rule.addItems(["保留原文件名", "添加前缀", "添加后缀"])
        self.naming_rule.currentIndexChanged.connect(self.update_naming_options)
        output_layout.addRow("命名规则:", self.naming_rule)

        self.name_modifier = QLineEdit("wm_")
        output_layout.addRow("前缀/后缀:", self.name_modifier)

        right_layout.addWidget(output_group)

        self.apply_btn = QPushButton("应用水印并导出")
        self.apply_btn.setStyleSheet("font-size: 14px; padding: 8px;")
        self.apply_btn.clicked.connect(self.apply_watermark)
        right_layout.addWidget(self.apply_btn)

        splitter.addWidget(right_panel)
        splitter.setSizes([320, 680])
        main_layout.addWidget(splitter)

        # 信号连接：点击图片切换预览
        self.image_list.itemSelectionChanged.connect(self.update_preview_from_selection)

        # 当预览控件内部 custom_pos 改变（拖拽后），需要主窗口把下拉框切换为“手动”
        # 这里通过定时检查 custom_pos 的方式检测拖拽后状态（简单且可靠）
        # 也可以在 WatermarkPreviewLabel 中暴露信号，这里为简洁使用定期更新
        # 我们使用 widget 的 mouse release 时更新一次：覆盖 preview_label.mouseReleaseEvent 并回调（更直接）
        # 为简单我们在鼠标释放后主动调用 update_preview_from_selection()
        # （实际拖拽过程中 preview 已实时更新）

        self.show()

    # ----------------- 文件 / 列表管理 -----------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path) and self.is_image_file(file_path):
                self.add_image(file_path)
            elif os.path.isdir(file_path):
                self.import_images_from_folder(file_path)
        event.acceptProposedAction()

    def is_image_file(self, file_path):
        supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']
        ext = os.path.splitext(file_path)[1].lower()
        return ext in supported_formats

    def import_images_from_folder(self, folder_path):
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff', '*.gif']
        image_files = []
        for ext in image_extensions:
            image_files.extend(glob.glob(os.path.join(folder_path, ext)))
        for image_file in sorted(image_files):
            self.add_image(image_file)

    def import_single_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "",
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff *.gif);;所有文件 (*)"
        )
        if file_path:
            self.add_image(file_path)

    def import_multiple_images(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择多张图片", "",
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff *.gif);;所有文件 (*)"
        )
        for file_path in file_paths:
            self.add_image(file_path)

    def import_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder_path:
            self.import_images_from_folder(folder_path)

    def add_image(self, file_path):
        if file_path not in self.image_paths:
            self.image_paths.append(file_path)
            item = QListWidgetItem()
            file_name = os.path.basename(file_path)
            item.setText(file_name)
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                item.setIcon(QIcon(scaled_pixmap))
            self.image_list.addItem(item)

    def remove_selected(self):
        for item in self.image_list.selectedItems():
            index = self.image_list.row(item)
            if 0 <= index < len(self.image_paths):
                del self.image_paths[index]
            self.image_list.takeItem(index)
        if self.image_list.count() == 0:
            self.preview_label.set_image(None)
            self.preview_label.update_preview_params(text="请选择一张图片")

    # ----------------- 预览与设置变更 -----------------
    def update_preview_from_selection(self):
        """当列表选择变化或设置变化时调用，更新 preview_label 的 image 与参数"""
        selected_items = self.image_list.selectedItems()
        if selected_items:
            index = self.image_list.row(selected_items[0])
            if 0 <= index < len(self.image_paths):
                image_path = self.image_paths[index]
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    self.preview_label.set_image(pixmap)
        else:
            self.preview_label.set_image(None)

        # 更新 preview 的参数（会触发绘制）
        self.preview_label.update_preview_params(
            text=self.watermark_text.text(),
            font_size=self.font_size.value(),
            color=self.watermark_color,
            opacity=self.opacity.value(),
            position_text=self.position.currentText()
        )

        # 如果用户完成拖拽（preview_label.custom_pos 被设置），我们需要把 position 下拉切换为 "手动"
        if self.preview_label.get_custom_pos_image_coords() is not None and self.position.currentText() != "手动":
            # 切换为手动模式
            idx = self.position.findText("手动")
            if idx >= 0:
                self.position.setCurrentIndex(idx)

    def on_setting_changed(self, *_):
        # 设置变更后实时更新预览；若用户之前拖拽过并处于手动模式，则保留 custom_pos
        self.update_preview_from_selection()

    def on_position_changed(self, index):
        # 当用户从下拉框选择预设/手动时，若切换到非手动则不清除 custom_pos（用户可能想恢复手动）
        # 但预览应根据 position_text 反映
        self.preview_label.update_preview_params(
            text=self.watermark_text.text(),
            font_size=self.font_size.value(),
            color=self.watermark_color,
            opacity=self.opacity.value(),
            position_text=self.position.currentText()
        )

    def choose_color(self):
        color = QColorDialog.getColor(self.watermark_color, self, "选择水印颜色")
        if color.isValid():
            self.watermark_color = color
            # 更新按钮样式
            if color.lightness() < 128:
                self.color_btn.setStyleSheet(f"background-color: {color.name()}; color: white;")
            else:
                self.color_btn.setStyleSheet(f"background-color: {color.name()}; color: black;")
            self.on_setting_changed()

    def choose_output_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if folder_path:
            self.output_folder.setText(folder_path)

    def update_naming_options(self, index):
        if index == 0:
            self.name_modifier.setEnabled(False)
        else:
            self.name_modifier.setEnabled(True)
            if index == 1:
                self.name_modifier.setText("wm_")
            else:
                self.name_modifier.setText("_wm")

    # ----------------- 导出（Pillow） -----------------
    def apply_watermark(self):
        if not self.image_paths:
            QMessageBox.warning(self, "警告", "请先导入图片")
            return

        output_folder = self.output_folder.text()
        if not output_folder:
            QMessageBox.warning(self, "警告", "请选择输出文件夹")
            return

        # 检查是否尝试导出到原文件夹（阻止覆盖）
        for image_path in self.image_paths:
            image_folder = os.path.dirname(image_path)
            if os.path.abspath(output_folder) == os.path.abspath(image_folder):
                QMessageBox.warning(self, "警告", "不能导出到原图片所在文件夹，以防止覆盖原图")
                return

        os.makedirs(output_folder, exist_ok=True)

        success_count = 0
        error_count = 0
        for image_path in self.image_paths:
            try:
                # 如果有选中并处于手动 mode，使用 preview_label 中的 custom_pos（必须和当前图片对应）
                custom_coords = None
                selected_items = self.image_list.selectedItems()
                if selected_items:
                    sel_index = self.image_list.row(selected_items[0])
                    # Only use preview custom pos if the selected item corresponds to this image_path
                    if 0 <= sel_index < len(self.image_paths) and self.image_paths[sel_index] == image_path:
                        if self.position.currentText() == "手动":
                            custom_coords = self.preview_label.get_custom_pos_image_coords()
                # 调用添加水印方法（支持 custom_coords）
                self.add_watermark_to_image(image_path, output_folder, custom_coords)
                success_count += 1
            except Exception as e:
                print(f"处理图片 {image_path} 时出错: {str(e)}")
                error_count += 1

        QMessageBox.information(self, "完成", f"处理完成！\n成功: {success_count} 张\n失败: {error_count} 张")

    def add_watermark_to_image(self, image_path, output_folder, custom_coords=None):
        """给单张图片添加水印并保存。custom_coords: (x_pixels, y_pixels) in original image coords used when position=='手动'"""
        # 打开图片
        with Image.open(image_path) as img:
            # 确保图片有Alpha通道（透明）
            orig_mode = img.mode
            if img.mode not in ('RGBA', 'LA'):
                if img.mode == 'P':
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGBA')

            watermark_layer = Image.new('RGBA', img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(watermark_layer)

            # 文本与字体
            text = self.watermark_text.text() or "Watermark"
            font_size = self.font_size.value()

            # 尝试加载系统字体（可根据需要调整路径）
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                try:
                    # 尝试常见路径（Linux/Mac 可能没有 arial）
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
                except Exception:
                    font = ImageFont.load_default()

            # 获取文本大小（兼容 Pillow 旧/新 API）
            try:
                text_width, text_height = draw.textsize(text, font=font)
            except AttributeError:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

            width, height = img.size
            position = self.position.currentText()

            # 计算文本位置（左上角坐标）在原图像像素坐标系
            if position == "手动" and custom_coords is not None:
                cx_img, cy_img = custom_coords
                x = int(cx_img - text_width / 2)
                y = int(cy_img - text_height / 2)
            else:
                margin = 10
                if position == "左上角":
                    x, y = margin, margin
                elif position == "上中":
                    x = (width - text_width) // 2
                    y = margin
                elif position == "右上角":
                    x = width - text_width - margin
                    y = margin
                elif position == "左中":
                    x = margin
                    y = (height - text_height) // 2
                elif position == "居中":
                    x = (width - text_width) // 2
                    y = (height - text_height) // 2
                elif position == "右中":
                    x = width - text_width - margin
                    y = (height - text_height) // 2
                elif position == "左下角":
                    x = margin
                    y = height - text_height - margin
                elif position == "下中":
                    x = (width - text_width) // 2
                    y = height - text_height - margin
                elif position == "右下角":
                    x = width - text_width - margin
                    y = height - text_height - margin
                else:
                    x = width - text_width - margin
                    y = height - text_height - margin

            # 颜色与透明度
            r, g, b, _ = self.watermark_color.getRgb()
            opacity = self.opacity.value()
            alpha = int(255 * opacity / 100)

            # 绘制文本到 watermark_layer
            draw.text((x, y), text, font=font, fill=(r, g, b, alpha))

            # 合成
            watermarked = Image.alpha_composite(img, watermark_layer)

            # 输出格式与文件名处理
            output_format = self.output_format.currentText().lower()
            file_name = os.path.basename(image_path)
            base_name, ext = os.path.splitext(file_name)

            naming_rule = self.naming_rule.currentIndex()
            if naming_rule == 1:
                new_base_name = f"{self.name_modifier.text()}{base_name}"
            elif naming_rule == 2:
                new_base_name = f"{base_name}{self.name_modifier.text()}"
            else:
                new_base_name = base_name

            output_file_name = f"{new_base_name}.{output_format}"
            output_path = os.path.join(output_folder, output_file_name)

            if output_format == 'jpeg' or output_format == 'jpg':
                # JPEG 不支持 alpha
                watermarked = watermarked.convert('RGB')

            watermarked.save(output_path)

# ----------------------
# 运行
# ----------------------
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = PhotoWatermarkApp()
    sys.exit(app.exec_())
