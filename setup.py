import sys
from cx_Freeze import setup, Executable

# 依赖项
build_exe_options = {
    "packages": ["os", "sys", "PIL", "traceback"],
    "includes": ["PyQt5", "PyQt5.QtWidgets", "PyQt5.QtGui", "PyQt5.QtCore"],
    "include_files": [],
    "excludes": [],
}

# 基础设置
base = None
if sys.platform == "win32":
    base = "Win32GUI"  # Windows 下不显示控制台窗口

# 应用信息
setup(
    name="PhotoWatermark2",
    version="1.0",
    description="Photo Watermark 2 - 图片水印工具",
    options={"build_exe": build_exe_options},
    executables=[Executable("main.py", base=base, target_name="PhotoWatermark2")]
)
