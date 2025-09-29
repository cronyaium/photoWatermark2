import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QFileDialog, QListWidget, 
                            QListWidgetItem, QLabel, QTabWidget, QGroupBox, 
                            QRadioButton, QLineEdit, QComboBox, QCheckBox,
                            QMessageBox, QSplitter, QFrame, QProgressBar)
from PyQt5.QtGui import QPixmap, QImage, QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
import PIL
from PIL import Image, ImageDraw, ImageFont
import traceback

class WatermarkThread(QThread):
    """处理水印添加的后台线程"""
    progress_updated = pyqtSignal(int)
    task_completed = pyqtSignal(bool, str)
    
    def __init__(self, image_paths, output_dir, watermark_text, 
                 font_path, font_size, opacity, position, 
                 output_format, prefix, suffix, keep_original_name):
        super().__init__()
        self.image_paths = image_paths
        self.output_dir = output_dir
        self.watermark_text = watermark_text
        self.font_path = font_path
        self.font_size = font_size
        self.opacity = opacity
        self.position = position
        self.output_format = output_format
        self.prefix = prefix
        self.suffix = suffix
        self.keep_original_name = keep_original_name
        
    def run(self):
        try:
            total = len(self.image_paths)
            for i, image_path in enumerate(self.image_paths):
                self.process_image(image_path)
                progress = int((i + 1) / total * 100)
                self.progress_updated.emit(progress)
            
            self.task_completed.emit(True, f"成功处理 {total} 张图片")
        except Exception as e:
            self.task_completed.emit(False, f"处理失败: {str(e)}\n{traceback.format_exc()}")
    
    def process_image(self, image_path):
        # 打开原图
        with Image.open(image_path) as img:
            # 创建水印图层
            watermark = Image.new('RGBA', img.size, (255, 255, 255, 0))
            
            # 加载字体
            try:
                font = ImageFont.truetype(self.font_path, self.font_size)
            except:
                #  fallback to default font if specified font is not available
                font = ImageFont.load_default()
            
            # 绘制水印文本
            draw = ImageDraw.Draw(watermark)
            text_bbox = draw.textbbox((0, 0), self.watermark_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # 根据位置计算水印坐标
            width, height = img.size
            x, y = 10, 10  # 默认左上角
            
            if self.position == "center":
                x = (width - text_width) // 2
                y = (height - text_height) // 2
            elif self.position == "bottom-right":
                x = width - text_width - 10
                y = height - text_height - 10
            elif self.position == "bottom-left":
                x = 10
                y = height - text_height - 10
            elif self.position == "top-right":
                x = width - text_width - 10
                y = 10
            
            # 绘制文本 (添加透明度)
            draw.text((x, y), self.watermark_text, font=font, 
                     fill=(255, 255, 255, int(self.opacity * 255)))
            
            # 合并原图和水印
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            combined = Image.alpha_composite(img, watermark)
            
            # 生成输出文件名
            filename = os.path.basename(image_path)
            name, ext = os.path.splitext(filename)
            
            if not self.keep_original_name:
                new_name = f"{self.prefix}{name}{self.suffix}.{self.output_format.lower()}"
            else:
                new_name = f"{name}.{self.output_format.lower()}"
            
            output_path = os.path.join(self.output_dir, new_name)
            
            # 保存图片
            if self.output_format.lower() == 'jpg':
                combined = combined.convert('RGB')
                combined.save(output_path, 'JPEG', quality=95)
            else:
                combined.save(output_path, 'PNG')

class PhotoWatermarkApp(QMainWindow):
    """Photo Watermark 2 主应用窗口"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.image_paths = []
        self.selected_output_dir = ""
        
    def init_ui(self):
        # 设置窗口标题和大小
        self.setWindowTitle("Photo Watermark 2")
        self.setGeometry(100, 100, 1000, 700)
        
        # 创建主部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建顶部按钮区域
        top_layout = QHBoxLayout()
        
        # 添加图片按钮
        self.add_btn = QPushButton("添加图片")
        self.add_btn.clicked.connect(self.add_images)
        top_layout.addWidget(self.add_btn)
        
        # 添加文件夹按钮
        self.add_folder_btn = QPushButton("添加文件夹")
        self.add_folder_btn.clicked.connect(self.add_folder)
        top_layout.addWidget(self.add_folder_btn)
        
        # 移除选中按钮
        self.remove_btn = QPushButton("移除选中")
        self.remove_btn.clicked.connect(self.remove_selected)
        top_layout.addWidget(self.remove_btn)
        
        # 清空按钮
        self.clear_btn = QPushButton("清空列表")
        self.clear_btn.clicked.connect(self.clear_list)
        top_layout.addWidget(self.clear_btn)
        
        main_layout.addLayout(top_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧图片列表
        self.image_list = QListWidget()
        self.image_list.setViewMode(QListWidget.IconMode)
        self.image_list.setIconSize(QSize(128, 128))
        self.image_list.setResizeMode(QListWidget.Adjust)
        self.image_list.setSelectionMode(QListWidget.ExtendedSelection)
        splitter.addWidget(self.image_list)
        
        # 右侧设置面板
        settings_panel = QWidget()
        settings_layout = QVBoxLayout(settings_panel)
        
        # 创建标签页
        tabs = QTabWidget()
        
        # 水印设置标签页
        watermark_tab = QWidget()
        watermark_layout = QVBoxLayout(watermark_tab)
        
        # 水印文本
        text_group = QGroupBox("水印文本")
        text_layout = QVBoxLayout(text_group)
        self.watermark_text = QLineEdit("我的水印")
        text_layout.addWidget(self.watermark_text)
        watermark_layout.addWidget(text_group)
        
        # 字体设置
        font_group = QGroupBox("字体设置")
        font_layout = QVBoxLayout(font_group)
        
        font_path_layout = QHBoxLayout()
        font_path_layout.addWidget(QLabel("字体文件:"))
        self.font_path = QLineEdit()
        font_path_layout.addWidget(self.font_path)
        self.font_browse_btn = QPushButton("浏览")
        self.font_browse_btn.clicked.connect(self.browse_font)
        font_path_layout.addWidget(self.font_browse_btn)
        font_layout.addLayout(font_path_layout)
        
        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("字体大小:"))
        self.font_size = QComboBox()
        for size in range(10, 72, 2):
            self.font_size.addItem(str(size))
        self.font_size.setCurrentText("24")
        font_size_layout.addWidget(self.font_size)
        font_layout.addLayout(font_size_layout)
        
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("透明度:"))
        self.opacity = QComboBox()
        for op in range(1, 10):
            self.opacity.addItem(f"{op * 10}%")
        self.opacity.setCurrentIndex(4)  # 50%
        opacity_layout.addWidget(self.opacity)
        font_layout.addLayout(opacity_layout)
        
        watermark_layout.addWidget(font_group)
        
        # 水印位置
        position_group = QGroupBox("水印位置")
        position_layout = QVBoxLayout(position_group)
        
        positions = [
            ("左上角", "top-left"),
            ("右上角", "top-right"),
            ("居中", "center"),
            ("左下角", "bottom-left"),
            ("右下角", "bottom-right")
        ]
        
        self.position_btns = {}
        for text, value in positions:
            btn = QRadioButton(text)
            self.position_btns[value] = btn
            position_layout.addWidget(btn)
        
        self.position_btns["bottom-right"].setChecked(True)  # 默认右下角
        watermark_layout.addWidget(position_group)
        
        tabs.addTab(watermark_tab, "水印设置")
        
        # 输出设置标签页
        output_tab = QWidget()
        output_layout = QVBoxLayout(output_tab)
        
        # 输出文件夹
        output_dir_group = QGroupBox("输出文件夹")
        output_dir_layout = QHBoxLayout(output_dir_group)
        self.output_dir = QLineEdit()
        output_dir_layout.addWidget(self.output_dir)
        self.browse_dir_btn = QPushButton("浏览")
        self.browse_dir_btn.clicked.connect(self.browse_output_dir)
        output_dir_layout.addWidget(self.browse_dir_btn)
        output_layout.addWidget(output_dir_group)
        
        # 输出格式
        format_group = QGroupBox("输出格式")
        format_layout = QHBoxLayout(format_group)
        self.jpg_radio = QRadioButton("JPEG")
        self.png_radio = QRadioButton("PNG")
        self.png_radio.setChecked(True)  # 默认PNG
        format_layout.addWidget(self.jpg_radio)
        format_layout.addWidget(self.png_radio)
        output_layout.addWidget(format_group)
        
        # 文件名设置
        filename_group = QGroupBox("文件名设置")
        filename_layout = QVBoxLayout(filename_group)
        
        self.keep_original_name = QCheckBox("保留原文件名")
        self.keep_original_name.setChecked(False)
        filename_layout.addWidget(self.keep_original_name)
        
        prefix_layout = QHBoxLayout()
        prefix_layout.addWidget(QLabel("前缀:"))
        self.filename_prefix = QLineEdit("wm_")
        prefix_layout.addWidget(self.filename_prefix)
        filename_layout.addLayout(prefix_layout)
        
        suffix_layout = QHBoxLayout()
        suffix_layout.addWidget(QLabel("后缀:"))
        self.filename_suffix = QLineEdit("_watermarked")
        suffix_layout.addWidget(self.filename_suffix)
        filename_layout.addLayout(suffix_layout)
        
        output_layout.addWidget(filename_group)
        
        tabs.addTab(output_tab, "输出设置")
        
        settings_layout.addWidget(tabs)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        settings_layout.addWidget(self.progress_bar)
        
        # 处理按钮
        self.process_btn = QPushButton("添加水印并导出")
        self.process_btn.clicked.connect(self.process_images)
        self.process_btn.setStyleSheet("font-size: 14px; padding: 8px;")
        settings_layout.addWidget(self.process_btn)
        
        splitter.addWidget(settings_panel)
        
        # 设置分割器比例
        splitter.setSizes([400, 600])
        
        main_layout.addWidget(splitter)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
    def add_images(self):
        """添加图片文件"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择图片", "", 
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff *.tif);;所有文件 (*)"
        )
        
        if file_paths:
            self.add_files_to_list(file_paths)
    
    def add_folder(self):
        """添加文件夹中的图片"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        
        if folder:
            image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif')
            file_paths = []
            
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(image_extensions):
                        file_paths.append(os.path.join(root, file))
            
            if file_paths:
                self.add_files_to_list(file_paths)
            else:
                QMessageBox.information(self, "提示", "所选文件夹中没有找到图片文件")
    
    def add_files_to_list(self, file_paths):
        """将文件添加到列表中"""
        added = 0
        for path in file_paths:
            if path not in self.image_paths:
                self.image_paths.append(path)
                
                # 创建列表项
                item = QListWidgetItem()
                item.setText(os.path.basename(path))
                
                # 创建缩略图
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    item.setIcon(QIcon(scaled_pixmap))
                
                self.image_list.addItem(item)
                added += 1
        
        if added > 0:
            self.statusBar().showMessage(f"已添加 {added} 张图片，共 {len(self.image_paths)} 张")
    
    def remove_selected(self):
        """移除选中的图片"""
        selected_items = self.image_list.selectedItems()
        if not selected_items:
            return
        
        for item in selected_items:
            index = self.image_list.row(item)
            self.image_paths.pop(index)
            self.image_list.takeItem(index)
        
        self.statusBar().showMessage(f"剩余 {len(self.image_paths)} 张图片")
    
    def clear_list(self):
        """清空图片列表"""
        if self.image_list.count() > 0:
            reply = QMessageBox.question(
                self, "确认", "确定要清空所有图片吗？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.image_list.clear()
                self.image_paths = []
                self.statusBar().showMessage("图片列表已清空")
    
    def browse_font(self):
        """浏览选择字体文件"""
        font_path, _ = QFileDialog.getOpenFileName(
            self, "选择字体文件", "", "字体文件 (*.ttf *.otf);;所有文件 (*)"
        )
        
        if font_path:
            self.font_path.setText(font_path)
    
    def browse_output_dir(self):
        """浏览选择输出文件夹"""
        output_dir = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        
        if output_dir:
            self.output_dir.setText(output_dir)
            self.selected_output_dir = output_dir
    
    def process_images(self):
        """处理图片，添加水印并导出"""
        # 检查是否有图片
        if not self.image_paths:
            QMessageBox.warning(self, "警告", "请先添加图片")
            return
        
        # 检查水印文本
        watermark_text = self.watermark_text.text().strip()
        if not watermark_text:
            QMessageBox.warning(self, "警告", "请输入水印文本")
            return
        
        # 检查输出文件夹
        output_dir = self.output_dir.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "警告", "请选择输出文件夹")
            return
        
        # 检查是否与原文件夹相同
        first_image_dir = os.path.dirname(self.image_paths[0])
        if output_dir == first_image_dir:
            reply = QMessageBox.question(
                self, "警告", 
                "输出文件夹与原图片文件夹相同，可能会覆盖原文件。是否继续？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
        
        # 创建输出文件夹（如果不存在）
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法创建输出文件夹: {str(e)}")
                return
        
        # 获取水印设置
        font_path = self.font_path.text().strip()
        if not font_path:
            # 使用默认字体
            font_path = self.get_default_font()
        
        try:
            font_size = int(self.font_size.currentText())
        except:
            font_size = 24
        
        try:
            opacity = int(self.opacity.currentText().replace("%", "")) / 100
        except:
            opacity = 0.5
        
        # 获取选中的位置
        position = "bottom-right"  # 默认
        for pos, btn in self.position_btns.items():
            if btn.isChecked():
                position = pos
                break
        
        # 获取输出格式
        output_format = "PNG" if self.png_radio.isChecked() else "JPEG"
        
        # 获取文件名设置
        keep_original_name = self.keep_original_name.isChecked()
        prefix = self.filename_prefix.text()
        suffix = self.filename_suffix.text()
        
        # 禁用按钮
        self.process_btn.setEnabled(False)
        self.add_btn.setEnabled(False)
        self.add_folder_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 创建并启动线程
        self.thread = WatermarkThread(
            self.image_paths, output_dir, watermark_text,
            font_path, font_size, opacity, position,
            output_format, prefix, suffix, keep_original_name
        )
        self.thread.progress_updated.connect(self.update_progress)
        self.thread.task_completed.connect(self.process_completed)
        self.thread.start()
    
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
        self.statusBar().showMessage(f"处理中... {value}%")
    
    def process_completed(self, success, message):
        """处理完成回调"""
        # 恢复按钮状态
        self.process_btn.setEnabled(True)
        self.add_btn.setEnabled(True)
        self.add_folder_btn.setEnabled(True)
        self.remove_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        
        # 隐藏进度条
        self.progress_bar.setVisible(False)
        
        # 显示结果消息
        if success:
            QMessageBox.information(self, "成功", message)
            self.statusBar().showMessage(message)
        else:
            QMessageBox.critical(self, "错误", message)
            self.statusBar().showMessage("处理失败")
    
    def get_default_font(self):
        """获取系统默认字体"""
        if sys.platform.startswith('win'):
            # Windows 系统默认字体
            return "C:/Windows/Fonts/arial.ttf"
        elif sys.platform.startswith('darwin'):
            # macOS 系统默认字体
            return "/System/Library/Fonts/Helvetica.ttc"
        else:
            # 其他系统（备用）
            return "/usr/share/fonts/truetype/freefont/FreeSans.ttf"

if __name__ == "__main__":
    # 确保中文显示正常
    import matplotlib
    matplotlib.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
    
    app = QApplication(sys.argv)
    window = PhotoWatermarkApp()
    window.show()
    sys.exit(app.exec_())
