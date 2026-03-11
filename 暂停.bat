@echo off
if "%1" == "hide" goto :hide
start /min cmd /c "%~f0" hide
exit
:hide
python click_image.py Pause.png

