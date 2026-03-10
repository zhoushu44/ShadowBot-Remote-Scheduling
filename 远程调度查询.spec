# -*- mode: python ; coding: utf-8 -*-
"""
远程调度查询 - PyInstaller配置文件
"""

a = Analysis(
    ['11.py'],
    pathex='.',
    binaries=[],
    datas=[],
    name='远程调度查询',
    appversion='1.0.0',
    description='远程调度查询工具 - 通过AI识别影刀运行状态',
    icon=None,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    distpath='dist',
    optimize=0,
)

exe = EXE(
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='远程调度查询',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    icon=None,
)
