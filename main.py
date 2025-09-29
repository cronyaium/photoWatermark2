import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QFileDialog, QListWidget, 
                            QListWidgetItem, QLabel, QComboBox, QLineEdit, 
                            QGroupBox, QFormLayout, QCheckBox, QSpinBox, 
                            QColorDialog, QMessageBox, QSplitter, QListWidget,
                            QFrame, QGridLayout)
from PyQt5.QtGui import QPixmap, QImage, QFont, QColor, QIcon
from PyQt5.QtCore import Qt, QSize, QUrl
from PIL import Image, ImageDraw, ImageFont, ImageOps
import glob

class PhotoWatermarkApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        
        # 存储导入的图片路径
        self.image_paths = []
        
        # 允许拖拽
        self.setAcceptDrops(True)
        
    def initUI(self):
        # 设置窗口标题和大小
        self.setWindowTitle('Photo Watermark 2')
        self.setGeometry(100, 100, 900, 600)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧面板 - 图片列表
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 导入按钮
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
        
        # 图片列表
        self.image_list = QListWidget()
        self.image_list.setViewMode(QListWidget.IconMode)
        self.image_list.setIconSize(QSize(128, 128))
        self.image_list.setResizeMode(QListWidget.Adjust)
        self.image_list.setSpacing(10)
        left_layout.addWidget(self.image_list)
        
        # 移除按钮
        self.remove_btn = QPushButton("移除选中图片")
        self.remove_btn.clicked.connect(self.remove_selected)
        left_layout.addWidget(self.remove_btn)
        
        splitter.addWidget(left_panel)
        
        # 右侧面板 - 水印设置和预览
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 预览区域
        preview_group = QGroupBox("预览")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_label = QLabel("请选择一张图片")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(300)
        self.preview_label.setStyleSheet("border: 1px solid #ccc;")
        preview_layout.addWidget(self.preview_label)
        right_layout.addWidget(preview_group)
        
        # 水印设置
        watermark_group = QGroupBox("水印设置")
        watermark_layout = QFormLayout(watermark_group)
        
        # 水印文本
        self.watermark_text = QLineEdit("Watermark")
        watermark_layout.addRow("水印文本:", self.watermark_text)
        
        # 字体大小
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 72)
        self.font_size.setValue(32)
        watermark_layout.addRow("字体大小:", self.font_size)
        
        # 透明度
        self.opacity = QSpinBox()
        self.opacity.setRange(10, 100)
        self.opacity.setValue(50)
        watermark_layout.addRow("透明度 (%):", self.opacity)
        
        # 颜色选择
        color_layout = QHBoxLayout()
        self.color_btn = QPushButton("选择颜色")
        self.color_btn.setStyleSheet("background-color: black; color: white;")
        self.color_btn.clicked.connect(self.choose_color)
        self.watermark_color = QColor(0, 0, 0)  # 默认黑色
        color_layout.addWidget(self.color_btn)
        watermark_layout.addRow("水印颜色:", color_layout)
        
        # 位置选择
        self.position = QComboBox()
        self.position.addItems(["左上角", "右上角", "居中", "左下角", "右下角"])
        watermark_layout.addRow("水印位置:", self.position)
        
        right_layout.addWidget(watermark_group)
        
        # 输出设置
        output_group = QGroupBox("输出设置")
        output_layout = QFormLayout(output_group)
        
        # 输出文件夹
        output_folder_layout = QHBoxLayout()
        self.output_folder = QLineEdit()
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.choose_output_folder)
        output_folder_layout.addWidget(self.output_folder)
        output_folder_layout.addWidget(self.browse_btn)
        output_layout.addRow("输出文件夹:", output_folder_layout)
        
        # 输出格式
        self.output_format = QComboBox()
        self.output_format.addItems(["JPEG", "PNG"])
        output_layout.addRow("输出格式:", self.output_format)
        
        # 命名规则
        self.naming_rule = QComboBox()
        self.naming_rule.addItems(["保留原文件名", "添加前缀", "添加后缀"])
        self.naming_rule.currentIndexChanged.connect(self.update_naming_options)
        output_layout.addRow("命名规则:", self.naming_rule)
        
        # 前缀/后缀输入
        self.name_modifier = QLineEdit("watermark_")
        output_layout.addRow("前缀/后缀:", self.name_modifier)
        
        right_layout.addWidget(output_group)
        
        # 应用水印按钮
        self.apply_btn = QPushButton("应用水印并导出")
        self.apply_btn.setStyleSheet("font-size: 14px; padding: 8px;")
        self.apply_btn.clicked.connect(self.apply_watermark)
        right_layout.addWidget(self.apply_btn)
        
        splitter.addWidget(right_panel)
        
        # 设置分割器比例
        splitter.setSizes([300, 600])
        
        main_layout.addWidget(splitter)
        
        # 连接信号槽
        self.image_list.itemSelectionChanged.connect(self.update_preview)
        
        self.show()
    
    # 拖拽相关方法
    def dragEnterEvent(self, event):
        # 检查拖入的是否是文件
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        # 处理拖入的文件
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                # 检查是否是图片文件
                if self.is_image_file(file_path):
                    self.add_image(file_path)
            elif os.path.isdir(file_path):
                # 如果是文件夹，导入所有图片
                self.import_images_from_folder(file_path)
        event.acceptProposedAction()
    
    # 检查文件是否为支持的图片格式
    def is_image_file(self, file_path):
        supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']
        ext = os.path.splitext(file_path)[1].lower()
        return ext in supported_formats
    
    # 从文件夹导入图片
    def import_images_from_folder(self, folder_path):
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff', '*.gif']
        image_files = []
        for ext in image_extensions:
            image_files.extend(glob.glob(os.path.join(folder_path, ext)))
        
        for image_file in image_files:
            self.add_image(image_file)
    
    # 导入单张图片
    def import_single_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", 
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff *.gif);;所有文件 (*)"
        )
        if file_path:
            self.add_image(file_path)
    
    # 导入多张图片
    def import_multiple_images(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择多张图片", "", 
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff *.gif);;所有文件 (*)"
        )
        for file_path in file_paths:
            self.add_image(file_path)
    
    # 导入文件夹
    def import_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder_path:
            self.import_images_from_folder(folder_path)
    
    # 添加图片到列表
    def add_image(self, file_path):
        if file_path not in self.image_paths:
            self.image_paths.append(file_path)
            
            # 创建列表项
            item = QListWidgetItem()
            file_name = os.path.basename(file_path)
            item.setText(file_name)
            
            # 创建缩略图
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                item.setIcon(QIcon(scaled_pixmap))
            
            self.image_list.addItem(item)
    
    # 移除选中的图片
    def remove_selected(self):
        for item in self.image_list.selectedItems():
            index = self.image_list.row(item)
            if index < len(self.image_paths):
                del self.image_paths[index]
            self.image_list.takeItem(index)
        
        # 更新预览
        if self.image_list.count() == 0:
            self.preview_label.setText("请选择一张图片")
    
    # 更新预览
    def update_preview(self):
        selected_items = self.image_list.selectedItems()
        if selected_items:
            index = self.image_list.row(selected_items[0])
            if 0 <= index < len(self.image_paths):
                image_path = self.image_paths[index]
                pixmap = QPixmap(image_path)
                
                if not pixmap.isNull():
                    # 缩放图片以适应预览区域
                    scaled_pixmap = pixmap.scaled(
                        self.preview_label.width(), self.preview_label.height(),
                        Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    self.preview_label.setPixmap(scaled_pixmap)
    
    # 选择水印颜色
    def choose_color(self):
        color = QColorDialog.getColor(self.watermark_color, self, "选择水印颜色")
        if color.isValid():
            self.watermark_color = color
            self.color_btn.setStyleSheet(f"background-color: {color.name()};")
            if color.lightness() < 128:
                self.color_btn.setStyleSheet(f"background-color: {color.name()}; color: white;")
            else:
                self.color_btn.setStyleSheet(f"background-color: {color.name()}; color: black;")
    
    # 选择输出文件夹
    def choose_output_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if folder_path:
            self.output_folder.setText(folder_path)
    
    # 更新命名选项显示
    def update_naming_options(self, index):
        if index == 0:  # 保留原文件名
            self.name_modifier.setEnabled(False)
        else:
            self.name_modifier.setEnabled(True)
            if index == 1:  # 添加前缀
                self.name_modifier.setText("wm_")
            else:  # 添加后缀
                self.name_modifier.setText("_wm")
    
    # 应用水印并导出
    def apply_watermark(self):
        if not self.image_paths:
            QMessageBox.warning(self, "警告", "请先导入图片")
            return
        
        output_folder = self.output_folder.text()
        if not output_folder:
            QMessageBox.warning(self, "警告", "请选择输出文件夹")
            return
        
        # 检查是否尝试导出到原文件夹
        for image_path in self.image_paths:
            image_folder = os.path.dirname(image_path)
            if os.path.abspath(output_folder) == os.path.abspath(image_folder):
                QMessageBox.warning(self, "警告", "不能导出到原图片所在文件夹，以防止覆盖原图")
                return
        
        # 创建输出文件夹（如果不存在）
        os.makedirs(output_folder, exist_ok=True)
        
        # 应用水印到所有图片
        success_count = 0
        error_count = 0
        
        for image_path in self.image_paths:
            try:
                self.add_watermark_to_image(image_path, output_folder)
                success_count += 1
            except Exception as e:
                print(f"处理图片 {image_path} 时出错: {str(e)}")
                error_count += 1
        
        QMessageBox.information(
            self, "完成", 
            f"处理完成！\n成功: {success_count} 张\n失败: {error_count} 张"
        )
    
    # 给单张图片添加水印
    def add_watermark_to_image(self, image_path, output_folder):
        # 打开图片
        with Image.open(image_path) as img:
            # 确保图片有Alpha通道（透明）
            if img.mode not in ('RGBA', 'LA'):
                if img.mode == 'P':
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGBA')
            
            # 创建水印层
            watermark = Image.new('RGBA', img.size, (255, 255, 255, 0))
            
            # 准备绘制水印
            draw = ImageDraw.Draw(watermark)
            
            # 获取水印文本和设置
            text = self.watermark_text.text()
            if not text.strip():
                text = "Watermark"  # 默认水印文本
            
            # 尝试加载字体
            try:
                # 尝试使用系统字体
                font = ImageFont.truetype("arial.ttf", self.font_size.value())
            except:
                # 如果没有找到指定字体，使用默认字体
                font = ImageFont.load_default()
                # 调整字体大小（默认字体较小）
                adjusted_size = int(self.font_size.value() * 0.7)
                font = ImageFont.load_default()
            
            # 获取文本大小（兼容 Pillow 新旧版本）
            try:
                text_width, text_height = draw.textsize(text, font=font)
            except AttributeError:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

            
            # 根据选择的位置计算文本位置
            x, y = 0, 0
            width, height = img.size
            
            position = self.position.currentText()
            if position == "左上角":
                x, y = 10, 10
            elif position == "右上角":
                x, y = width - text_width - 10, 10
            elif position == "居中":
                x, y = (width - text_width) // 2, (height - text_height) // 2
            elif position == "左下角":
                x, y = 10, height - text_height - 10
            elif position == "右下角":
                x, y = width - text_width - 10, height - text_height - 10
            
            # 获取颜色和透明度
            r, g, b, _ = self.watermark_color.getRgb()
            opacity = self.opacity.value()
            
            # 绘制水印
            draw.text(
                (x, y), 
                text, 
                font=font, 
                fill=(r, g, b, int(255 * opacity / 100))
            )
            
            # 合并图片和水印
            watermarked_img = Image.alpha_composite(img, watermark)
            
            # 处理输出格式
            output_format = self.output_format.currentText().lower()
            
            # 生成输出文件名
            file_name = os.path.basename(image_path)
            base_name, ext = os.path.splitext(file_name)
            
            naming_rule = self.naming_rule.currentIndex()
            if naming_rule == 1:  # 添加前缀
                new_base_name = f"{self.name_modifier.text()}{base_name}"
            elif naming_rule == 2:  # 添加后缀
                new_base_name = f"{base_name}{self.name_modifier.text()}"
            else:  # 保留原文件名
                new_base_name = base_name
            
            output_file_name = f"{new_base_name}.{output_format}"
            output_path = os.path.join(output_folder, output_file_name)
            
            # 如果是JPEG格式，需要转换为RGB
            if output_format == 'jpeg':
                watermarked_img = watermarked_img.convert('RGB')
            
            # 保存图片
            watermarked_img.save(output_path)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = PhotoWatermarkApp()
    sys.exit(app.exec_())
    