# Photo Watermark 2

一个简单易用的图片水印工具，支持批量处理图片并添加自定义水印。

## 功能特点

- 支持单张或批量导入图片
- 支持拖拽添加图片
- 支持主流图片格式（JPEG, PNG, BMP, TIFF）
- 自定义水印文本、字体、大小和透明度
- 可选择水印位置（左上角、右上角、居中、左下角、右下角）
- 灵活的输出设置，包括输出格式和文件名规则
- 防止覆盖原图的安全机制

## 安装与使用

### 直接运行

从 [Releases](https://github.com/yourusername/photo-watermark-2/releases) 页面下载对应系统的最新版本，解压后即可运行。

- Windows: 运行 `PhotoWatermark2.exe`
- macOS: 运行 `PhotoWatermark2.app`

### 从源码运行

1. 克隆仓库:
   ```
   git clone https://github.com/yourusername/photo-watermark-2.git
   cd photo-watermark-2
   ```

2. 安装依赖:
   ```
   pip install -r requirements.txt
   ```

3. 运行应用:
   ```
   python main.py
   ```

## 使用方法

1. 点击"添加图片"按钮或直接拖拽图片到左侧列表
2. 在右侧设置水印文本、字体、大小、透明度和位置
3. 选择输出文件夹、输出格式和文件名规则
4. 点击"添加水印并导出"按钮开始处理

## 打包应用

如需自己打包应用，可以使用以下命令:
# Windows
python setup.py build

# macOS (需要使用cx_Freeze或py2app)
python setup.py bdist_mac
## 许可证

本项目采用 MIT 许可证 - 详见 LICENSE 文件
