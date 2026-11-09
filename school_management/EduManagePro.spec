# -*- mode: python ; coding: utf-8 -*-
# PyInstaller Spec for EduManage Pro Windows Build

import sys
from pathlib import Path

block_cipher = None
base_dir = Path.cwd()

a = Analysis(
    ['app/main.py'],
    pathex=[str(base_dir)],
    binaries=[],
    datas=[
        ('app/config', 'app/config'),
        ('app/ui/themes', 'app/ui/themes'),
    ],
    hiddenimports=[
        'sqlalchemy.ext.baked',
        'sqlalchemy.sql.default_comparator',
        'bcrypt',
        'sqlite3',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'numpy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='EduManagePro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='EduManagePro',
)
