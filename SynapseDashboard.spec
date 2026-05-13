# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ['SynapseDashboard.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)
exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='SynapseDashboard',
    debug=False,
    strip=False,
    upx=False,
    console=True,
    icon=None,
)
