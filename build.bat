@echo off
REM ============================================
REM  JM Downloader 打包脚本（PyInstaller）
REM  用法: 双击运行，产物在 dist\jm-downloader.exe
REM ============================================
chcp 65001 >nul
cd /d %~dp0

echo [1/2] 安装依赖...
python -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ -q
python -m pip install pyinstaller -i https://mirrors.aliyun.com/pypi/simple/ -q

echo [2/2] 打包 exe...
python -m PyInstaller --noconfirm --clean --onefile --console ^
  --name jm-downloader ^
  --collect-all jmcomic ^
  main.py

echo.
echo 完成！产物: dist\jm-downloader.exe
pause
