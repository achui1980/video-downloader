import os
import sys
import PyInstaller.__main__

# 设置应用图标路径(假设你有一个图标文件)
icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'icon.svg')
# 如果没有图标，可以注释掉相关的 --icon 参数

# 确定需要包含的附加文件
additional_files = [
    ('LICENSE', '.'),
    ('README.md', '.'),
    ('icons', 'assets'),  # 假设有icons文件夹
]

# 构建打包参数
params = [
    'main.py',  # 程序入口点
    '--name=VideoDownloader',  # 生成的exe文件名
    '--onefile',  # 单文件模式
    '--windowed',  # GUI应用，不显示控制台
    # '--icon=' + icon_path,  # 如果有图标，取消此行注释
    '--clean',  # 清理临时文件
]

# 检查并添加模板和静态文件
if os.path.exists('templates'):
    params.append('--add-data=templates;templates' if sys.platform.startswith('win') else '--add-data=templates:templates')
if os.path.exists('static'):
    params.append('--add-data=static;static' if sys.platform.startswith('win') else '--add-data=static:static')

# 添加附加文件
for src, dst in additional_files:
    if os.path.exists(src):
        separator = ';' if sys.platform.startswith('win') else ':'
        params.append(f'--add-data={src}{separator}{dst}')

# 运行PyInstaller
print("开始打包应用...")
PyInstaller.__main__.run(params)

print("打包完成！可执行文件位于 dist 文件夹中。")
