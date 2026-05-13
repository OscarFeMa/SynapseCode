# -*- mode: python ; coding: utf-8 -*-
import os
ROOT = os.getcwd()

a = Analysis(
    ['SynapseDashboard.py'],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, "frontend", "admin.html"), "frontend"),
    ],
    hiddenimports=[
        'tkinter', 'tkinter.ttk', 'tkinter.messagebox',
        'urllib.request', 'urllib.error',
        'json', 'threading', 'webbrowser', 'subprocess', 'time',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
        'matplotlib', 'numpy', 'pandas', 'PIL', 'Pillow',
        'notebook', 'jupyter', 'tensorflow', 'torch',
    ],
    win_no_prefer_redirects=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

icon_path = os.path.join(ROOT, "desktop", "assets", "icon.ico")
icon_arg = icon_path if os.path.exists(icon_path) else None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SynapseDashboard',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=icon_arg,
)
