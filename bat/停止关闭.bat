@echo off
if "%1" == "hide" goto :hide
start /min cmd /c "%~f0" hide
exit
:hide
python click_image.py Stop.png
timeout /t 4 /nobreak >nul
python click_image.py Close.png

