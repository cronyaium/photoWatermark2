# main.py
import sys
import os
import glob
import json
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QFileDialog, QListWidget,
                             QListWidgetItem, QLabel, QComboBox, QLineEdit,
                             QGroupBox, QFormLayout, QSpinBox,
                             QColorDialog, QMessageBox, QSplitter, QInputDialog)
from PyQt5.QtGui import QPixmap, QFont, QColor, QIcon, QPainter, QFontMetrics, QFontDatabase
from PyQt5.QtCore import Qt, QSize, QPoint, QRect, pyqtSignal
from PIL import Image, ImageDraw, ImageFont

# ----------------------
# 配置：模板目录与 last used 文件名
# ----------------------
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
LAST_USED_FILENAME = "last_used.json"

# ----------------------
# 帮助寻找系统字体路径（常见位置）
# ----------------------
def find_system_font_path():
    candidates = [
        # Windows 常见
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\ARIAL.TTF",
        r"C:\Windows\Fonts\msyh.ttf",
        # Linux 常见
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        # macOS 常见
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/SFNSText.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

# ----------------------
# 可拖拽且直接绘制水印的预览 QLabel
# ----------------------
class WatermarkPreviewLabel(QLabel):
    # 拖拽后发出信号，主窗口会监听以自动切换到手动模式
    customPosChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.base_pixmap = None  # 原始 QPixmap（完整像素）
        self.display_pixmap = None  # 缩放到 widget 的 QPixmap（绘制用）
        self.img_width = 0
        self.img_height = 0

        # 水印参数（字体大小表示“原始图片上的像素大小”）
        self.text = "Watermark"
        self.font_size = 32  # 原图像像素为单位
        self.color = QColor(0, 0, 0)
        self.opacity = 50
        self.position_text = "右下角"  # 预设位置名称或 "手动"

        # 字体家族（若通过 QFontDatabase 注册了外部字体，会放这里）
        self.font_family = None

        # custom position（原图像像素坐标，中心点锚）
        self.custom_pos = None

        # 拖拽状态
        self.dragging = False
        self.drag_offset = QPoint(0, 0)

        # 用于点击检测的上次文字矩形（display coords）
        self.last_text_rect = None

    def set_font_family(self, family_name):
        self.font_family = family_name

    def set_image(self, pixmap: QPixmap):
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

    def update_display_pixmap(self):
        if not self.base_pixmap:
            self.display_pixmap = None
            return
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            self.display_pixmap = self.base_pixmap
            return
        self.display_pixmap = self.base_pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def update_preview_params(self, text=None, font_size=None, color=None, opacity=None, position_text=None):
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
        self.update_display_pixmap()
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)

        if not self.display_pixmap:
            painter.drawText(self.rect(), Qt.AlignCenter, "请选择一张图片")
            painter.end()
            return

        dp = self.display_pixmap
        dw = dp.width()
        dh = dp.height()
        x = (self.width() - dw) // 2
        y = (self.height() - dh) // 2

        painter.drawPixmap(x, y, dp)

        # scale: 原始 image pixels -> display pixels 的缩放比例 （统一用 x 方向）
        scale = (dw / self.img_width) if (self.img_width and dw) else 1.0

        # 设定 QFont 的像素大小为 原始像素大小 * scale -> 这样预览字体和导出字体按比例一致
        display_font_px = max(1, int(self.font_size * scale))

        qfont = QFont()
        if self.font_family:
            qfont.setFamily(self.font_family)
        qfont.setPixelSize(display_font_px)
        painter.setFont(qfont)
        fm = QFontMetrics(qfont)
        text = self.text
        text_w = fm.horizontalAdvance(text)
        text_h = fm.height()

        margin = 10
        pos_name = self.position_text

        if pos_name == "手动" and self.custom_pos is not None:
            cx_img, cy_img = self.custom_pos
            disp_cx = int(cx_img * scale) + x
            disp_cy = int(cy_img * scale) + y
            tx = disp_cx - text_w // 2
            ty = disp_cy - text_h // 2
        else:
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
                tx = x + dw - text_w - margin
                ty = y + dh - text_h - margin

        self.last_text_rect = QRect(tx, ty, text_w, text_h)

        color = QColor(self.color)
        alpha = max(0, min(255, int(255 * (self.opacity / 100.0))))
        color.setAlpha(alpha)
        painter.setPen(color)

        painter.drawText(tx, ty + fm.ascent(), text)
        painter.end()

    def mousePressEvent(self, event):
        if not self.display_pixmap:
            return super().mousePressEvent(event)

        if event.button() == Qt.LeftButton:
            pt = event.pos()
            if self.last_text_rect and self.last_text_rect.contains(pt):
                self.dragging = True
                center = self.last_text_rect.center()
                self.drag_offset = pt - center
                event.accept()
            else:
                super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging and self.display_pixmap:
            pt = event.pos()
            center_disp_x = pt.x() - self.drag_offset.x()
            center_disp_y = pt.y() - self.drag_offset.y()

            dp = self.display_pixmap
            dw = dp.width()
            dh = dp.height()
            img_x = (self.width() - dw) // 2
            img_y = (self.height() - dh) // 2
            scale = (dw / self.img_width) if (self.img_width and dw) else 1.0

            cx_img = (center_disp_x - img_x) / scale
            cy_img = (center_disp_y - img_y) / scale

            cx_img = max(0, min(self.img_width, cx_img))
            cy_img = max(0, min(self.img_height, cy_img))

            self.custom_pos = (cx_img, cy_img)
            # 拖拽过程中也发信号（主窗口会切换到手动）
            self.customPosChanged.emit()
            self.update()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = False
            # 确保释放后也通知一次（以便主窗口立即切换为手动）
            self.customPosChanged.emit()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def clear_custom_pos(self):
        self.custom_pos = None
        self.update()

    def get_custom_pos_image_coords(self):
        return self.custom_pos

# ----------------------
# 主窗口
# ----------------------
class PhotoWatermarkApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.font_path = find_system_font_path()  # 尝试找一个系统字体以在 Pillow 中使用
        self.font_family = None  # 若成功在 Qt 中注册会填上
        # 确保模板目录存在
        os.makedirs(TEMPLATES_DIR, exist_ok=True)
        self.initUI()

        self.image_paths = []
        self.setAcceptDrops(True)

        # 程序启动时尝试加载 last used 设置
        self.load_last_used_template_if_exists()
        # 刷新模板下拉
        self.refresh_template_list()

    def initUI(self):
        self.setWindowTitle('Photo Watermark 2')
        self.setGeometry(100, 100, 1000, 640)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        splitter = QSplitter(Qt.Horizontal)

        # 左侧
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

        # 右侧
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        preview_group = QGroupBox("预览")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_label = WatermarkPreviewLabel()
        self.preview_label.setMinimumHeight(360)
        self.preview_label.setStyleSheet("border: 1px solid #ccc; background: #fff;")
        preview_layout.addWidget(self.preview_label)
        right_layout.addWidget(preview_group)

        # 如果找到了字体路径，尝试在 Qt 中注册以保证预览与 Pillow 字体家族一致
        if self.font_path:
            try:
                font_id = QFontDatabase.addApplicationFont(self.font_path)
                if font_id != -1:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    if families:
                        self.font_family = families[0]
                        self.preview_label.set_font_family(self.font_family)
            except Exception:
                self.font_family = None

        watermark_group = QGroupBox("水印设置")
        watermark_layout = QFormLayout(watermark_group)
        self.watermark_text = QLineEdit("Watermark")
        self.watermark_text.textChanged.connect(self.on_setting_changed)
        watermark_layout.addRow("水印文本:", self.watermark_text)

        self.font_size = QSpinBox()
        self.font_size.setRange(8, 400)
        self.font_size.setValue(32)
        self.font_size.valueChanged.connect(self.on_setting_changed)
        watermark_layout.addRow("字体大小 (像素):", self.font_size)

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
        self.position.addItems(["左上角", "上中", "右上角", "左中", "居中", "右中", "左下角", "下中", "右下角", "手动"])
        self.position.currentIndexChanged.connect(self.on_position_changed)
        watermark_layout.addRow("水印位置:", self.position)

        # 模板管理行（放在水印设置中，尽量不改变原有位置结构）
        tpl_hbox = QHBoxLayout()
        self.template_combo = QComboBox()
        self.template_combo.setEditable(False)
        self.template_combo.currentIndexChanged.connect(self.on_template_selected)
        tpl_hbox.addWidget(self.template_combo)
        self.save_template_btn = QPushButton("保存为模板")
        self.save_template_btn.clicked.connect(self.save_current_as_template)
        tpl_hbox.addWidget(self.save_template_btn)
        self.delete_template_btn = QPushButton("删除模板")
        self.delete_template_btn.clicked.connect(self.delete_selected_template)
        tpl_hbox.addWidget(self.delete_template_btn)
        watermark_layout.addRow("模板管理:", tpl_hbox)

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

        # 信号连接
        self.image_list.itemSelectionChanged.connect(self.update_preview_from_selection)
        self.preview_label.customPosChanged.connect(self.on_preview_custom_pos_changed)

        self.show()

    # ---------- drag & drop / list ----------
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

    # ---------- 预览与设置变更 ----------
    def update_preview_from_selection(self):
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

        self.preview_label.update_preview_params(
            text=self.watermark_text.text(),
            font_size=self.font_size.value(),
            color=self.watermark_color,
            opacity=self.opacity.value(),
            position_text=self.position.currentText()
        )

        # 在切换图片或更新预览时，保存 last used 设置
        self.save_last_used_template()

    def on_setting_changed(self, *_):
        self.update_preview_from_selection()
        # 实时保存当前设置为 last_used
        self.save_last_used_template()

    def on_position_changed(self, index):
        self.preview_label.update_preview_params(
            text=self.watermark_text.text(),
            font_size=self.font_size.value(),
            color=self.watermark_color,
            opacity=self.opacity.value(),
            position_text=self.position.currentText()
        )
        # 保存 last used
        self.save_last_used_template()

    def on_preview_custom_pos_changed(self):
        # 预览控件发来拖拽事件 -> 自动切换为手动
        if self.position.currentText() != "手动":
            idx = self.position.findText("手动")
            if idx >= 0:
                self.position.setCurrentIndex(idx)
        # 更新 preview（已由 preview 自身更新过，但保持同步）
        self.preview_label.update_preview_params(
            text=self.watermark_text.text(),
            font_size=self.font_size.value(),
            color=self.watermark_color,
            opacity=self.opacity.value(),
            position_text=self.position.currentText()
        )
        # 拖拽后保存 last used（以保留 custom_pos）
        self.save_last_used_template()

    def choose_color(self):
        color = QColorDialog.getColor(self.watermark_color, self, "选择水印颜色")
        if color.isValid():
            self.watermark_color = color
            if color.lightness() < 128:
                self.color_btn.setStyleSheet(f"background-color: {color.name()}; color: white;")
            else:
                self.color_btn.setStyleSheet(f"background-color: {color.name()}; color: black;")
            self.on_setting_changed()

    def choose_output_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if folder_path:
            self.output_folder.setText(folder_path)
            # 保存 last used folder
            self.save_last_used_template()

    def update_naming_options(self, index):
        if index == 0:
            self.name_modifier.setEnabled(False)
        else:
            self.name_modifier.setEnabled(True)
            if index == 1:
                self.name_modifier.setText("wm_")
            else:
                self.name_modifier.setText("_wm")

    # ---------- 模板管理 ----------
    def template_file_path(self, name):
        safe_name = f"{name}.json"
        return os.path.join(TEMPLATES_DIR, safe_name)

    def refresh_template_list(self):
        """扫描 templates/ 并刷新下拉框（第一个项为 -- 无 -- ）"""
        self.template_combo.blockSignals(True)
        self.template_combo.clear()
        files = []
        try:
            for f in os.listdir(TEMPLATES_DIR):
                if f.endswith(".json"):
                    files.append(f)
            files = sorted(files)
            # 放一个空项或 "选择模板"
            self.template_combo.addItem("-- 选择模板 --")
            for f in files:
                if f == LAST_USED_FILENAME:
                    continue
                name = f[:-5]
                self.template_combo.addItem(name)
        except Exception:
            # ignore
            pass
        self.template_combo.blockSignals(False)

    def save_current_as_template(self):
        name, ok = QInputDialog.getText(self, "保存模板", "模板名称：")
        if not ok:
            return
        name = name.strip()
        if not name:
            # 为空则使用时间戳
            name = f"tpl_{int(time.time())}"
        # 准备对象
        tpl = self._collect_current_settings(include_custom_pos=True)
        # 写入文件（覆盖同名）
        try:
            with open(self.template_file_path(name), "w", encoding="utf-8") as f:
                json.dump(tpl, f, ensure_ascii=False, indent=2)
            # 刷新下拉并选中该模板
            self.refresh_template_list()
            idx = self.template_combo.findText(name)
            if idx >= 0:
                self.template_combo.setCurrentIndex(idx)
            QMessageBox.information(self, "保存成功", f"模板 '{name}' 已保存到 templates/ 目录（同名会覆盖）")
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"保存模板时出错: {e}")

    def delete_selected_template(self):
        name = self.template_combo.currentText()
        if not name or name == "-- 选择模板 --":
            QMessageBox.information(self, "提示", "请选择要删除的模板")
            return
        path = self.template_file_path(name)
        if os.path.exists(path):
            try:
                os.remove(path)
                QMessageBox.information(self, "删除成功", f"模板 '{name}' 已删除")
            except Exception as e:
                QMessageBox.warning(self, "删除失败", f"删除模板时出错: {e}")
        else:
            QMessageBox.information(self, "提示", "模板文件不存在")
        self.refresh_template_list()

    def on_template_selected(self, index):
        name = self.template_combo.currentText()
        if not name or name == "-- 选择模板 --":
            return
        self.load_template_by_name(name)

    def load_template_by_name(self, name):
        path = self.template_file_path(name)
        if not os.path.exists(path):
            QMessageBox.information(self, "提示", "模板文件不存在")
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                tpl = json.load(f)
            # 应用模板到 UI（不改变输出 folder 等）
            self._apply_template_to_ui(tpl)
            # 保存为 last used
            self.save_last_used_template()
            QMessageBox.information(self, "加载成功", f"模板 '{name}' 已应用")
        except Exception as e:
            QMessageBox.warning(self, "加载失败", f"加载模板时出错: {e}")

    def _collect_current_settings(self, include_custom_pos=False):
        """收集当前 UI 的水印设置为 dict，便于序列化"""
        tpl = {
            "text": self.watermark_text.text(),
            "font_size": self.font_size.value(),
            "opacity": self.opacity.value(),
            "color": list(self.watermark_color.getRgb()[:3]),  # RGB
            "position": self.position.currentText(),
            "output_format": self.output_format.currentText(),
            "naming_rule": self.naming_rule.currentIndex(),
            "name_modifier": self.name_modifier.text(),
            "output_folder": self.output_folder.text()
        }
        if include_custom_pos:
            cp = self.preview_label.get_custom_pos_image_coords()
            if cp is not None:
                tpl["custom_pos"] = [float(cp[0]), float(cp[1])]
            else:
                tpl["custom_pos"] = None
        return tpl

    def _apply_template_to_ui(self, tpl):
        """将模板内容应用回 UI（尽量不修改文件列表）"""
        try:
            self.watermark_text.setText(tpl.get("text", ""))
            self.font_size.setValue(int(tpl.get("font_size", 32)))
            self.opacity.setValue(int(tpl.get("opacity", 50)))
            col = tpl.get("color", [0, 0, 0])
            if isinstance(col, (list, tuple)) and len(col) >= 3:
                self.watermark_color = QColor(col[0], col[1], col[2])
                # update color button style
                if self.watermark_color.lightness() < 128:
                    self.color_btn.setStyleSheet(f"background-color: {self.watermark_color.name()}; color: white;")
                else:
                    self.color_btn.setStyleSheet(f"background-color: {self.watermark_color.name()}; color: black;")
            pos = tpl.get("position", "右下角")
            idx = self.position.findText(pos)
            if idx >= 0:
                self.position.setCurrentIndex(idx)
            # output format / naming rule / output folder
            of = tpl.get("output_format", None)
            if of:
                idx2 = self.output_format.findText(of)
                if idx2 >= 0:
                    self.output_format.setCurrentIndex(idx2)
            nr = tpl.get("naming_rule", None)
            if isinstance(nr, int):
                if 0 <= nr < self.naming_rule.count():
                    self.naming_rule.setCurrentIndex(nr)
            nm = tpl.get("name_modifier", None)
            if nm is not None:
                self.name_modifier.setText(nm)
            ofolder = tpl.get("output_folder", None)
            if ofolder:
                self.output_folder.setText(ofolder)
            # custom pos
            cp = tpl.get("custom_pos", None)
            if cp is not None and isinstance(cp, (list, tuple)) and len(cp) >= 2:
                # set preview_label custom_pos and switch to 手动
                self.preview_label.custom_pos = (float(cp[0]), float(cp[1]))
                idxm = self.position.findText("手动")
                if idxm >= 0:
                    self.position.setCurrentIndex(idxm)
            else:
                # 如果模板没有 custom pos，则不改变 preview_label.custom_pos（保持现状）
                pass

            # 更新 preview
            self.update_preview_from_selection()
        except Exception:
            # 忽略单项失败，尽量应用其他项
            self.update_preview_from_selection()

    # ---------- last used 存取 ----------
    def save_last_used_template(self):
        tpl = self._collect_current_settings(include_custom_pos=True)
        last_used_path = os.path.join(TEMPLATES_DIR, LAST_USED_FILENAME)
        try:
            with open(last_used_path, "w", encoding="utf-8") as f:
                json.dump(tpl, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # 不阻塞主流程

    def load_last_used_template_if_exists(self):
        last_used_path = os.path.join(TEMPLATES_DIR, LAST_USED_FILENAME)
        if os.path.exists(last_used_path):
            try:
                with open(last_used_path, "r", encoding="utf-8") as f:
                    tpl = json.load(f)
                # apply to UI but don't overwrite file list etc.
                self._apply_template_to_ui(tpl)
            except Exception:
                pass

    # ---------- 导出（Pillow） ----------
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
                # 如果当前选中项并处在手动 mode -> 使用 preview 的 custom_pos（原图像像素）
                custom_coords = None
                selected_items = self.image_list.selectedItems()
                if selected_items:
                    sel_index = self.image_list.row(selected_items[0])
                    if 0 <= sel_index < len(self.image_paths) and self.image_paths[sel_index] == image_path:
                        if self.position.currentText() == "手动":
                            custom_coords = self.preview_label.get_custom_pos_image_coords()
                self.add_watermark_to_image(image_path, output_folder, custom_coords)
                success_count += 1
            except Exception as e:
                print(f"处理图片 {image_path} 时出错: {e}")
                error_count += 1

        QMessageBox.information(self, "完成", f"处理完成！\n成功: {success_count} 张\n失败: {error_count} 张")

    def add_watermark_to_image(self, image_path, output_folder, custom_coords=None):
        with Image.open(image_path) as img:
            orig_mode = img.mode
            if img.mode not in ('RGBA', 'LA'):
                if img.mode == 'P':
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGBA')

            draw_layer = Image.new('RGBA', img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(draw_layer)

            text = self.watermark_text.text() or "Watermark"
            font_size = self.font_size.value()  # 这是“原图像上的像素大小”

            # 优先使用找到的系统字体路径
            pil_font = None
            if self.font_path:
                try:
                    pil_font = ImageFont.truetype(self.font_path, font_size)
                except Exception:
                    pil_font = None
            if pil_font is None:
                try:
                    pil_font = ImageFont.truetype("arial.ttf", font_size)
                except Exception:
                    pil_font = ImageFont.load_default()

            # 文本尺寸（兼容旧/新 pillow）
            try:
                text_width, text_height = draw.textsize(text, font=pil_font)
            except AttributeError:
                bbox = draw.textbbox((0, 0), text, font=pil_font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

            width, height = img.size
            position = self.position.currentText()
            margin = 10

            if position == "手动" and custom_coords is not None:
                cx_img, cy_img = custom_coords
                x = int(cx_img - text_width / 2)
                y = int(cy_img - text_height / 2)
            else:
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

            r, g, b, _ = self.watermark_color.getRgb()
            opacity = self.opacity.value()
            alpha = int(255 * opacity / 100)

            draw.text((x, y), text, font=pil_font, fill=(r, g, b, alpha))

            watermarked = Image.alpha_composite(img, draw_layer)
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

            if output_format in ('jpeg', 'jpg'):
                watermarked = watermarked.convert('RGB')

            watermarked.save(output_path)

# ----------------------
# 运行
# ----------------------
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = PhotoWatermarkApp()
    sys.exit(app.exec_())
