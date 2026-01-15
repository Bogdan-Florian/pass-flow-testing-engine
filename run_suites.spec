# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['run_suites.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['sqlalchemy.dialects.sqlite', 'sqlalchemy.dialects.postgresql', 'sqlalchemy.dialects.mysql', 'paramiko', 'openpyxl', 'xlrd'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'IPython', 'jupyter', 'pytest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='run_suites',
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
    entitlements_file=None,
)
