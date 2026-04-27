# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec 文件
# 打包模式：onefile（单文件 exe），FFmpeg 不内嵌，用户把 ffmpeg.exe/ffprobe.exe 丢同级目录即可

block_cipher = None

a = Analysis(
    ['加片头片尾4.4_简洁高级分层_UI优化版.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'numpy', 'pandas', 'matplotlib', 'scipy',
        'PIL', 'cv2', 'torch', 'tensorflow',
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
        'wx', 'gi',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,      # onefile 模式：binaries 合入 exe
    a.datas,         # onefile 模式：datas 合入 exe
    [],
    name='视频片头片尾批处理工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,               # 不显示命令行黑窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=r'C:\Users\王二狗\Documents\Codex\2026-04-25\nas\dist\NAS-TV-Organizer\_internal\assets\OIG.ico',
)
