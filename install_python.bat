@echo off

rem 检查 Python 是否安装
echo 检查 Python 安装...
python --version >nul 2>&1
if errorlevel 1 (
    echo 未找到 Python，开始自动安装...
    
    rem 下载 Python 安装包
    echo 正在下载 Python...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe' -OutFile 'python-installer.exe'"
    
    rem 安装 Python
    echo 正在安装 Python...
    start /wait python-installer.exe /quiet InstallAllUsers=1 PrependPath=1
    
    rem 清理安装包
    del python-installer.exe
    
    rem 刷新环境变量
    echo 正在刷新环境变量...
    set PATH=%PATH%;C:\Program Files\Python312;C:\Program Files\Python312\Scripts
    
    echo Python 安装完成！
)

echo Python 已就绪，准备运行脚本...
pause
