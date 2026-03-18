# -*- mode: python ; coding: utf-8 -*-
# Discord Auto Sender — build.spec
# Сборка через GitHub Actions: pyinstaller build.spec

import os
block_cipher = None

# Собираем список ресурсов — добавляем только те файлы которые существуют
datas = []
if os.path.exists('icon.ico'):
    datas.append(('icon.ico', '.'))
if os.path.exists('icon.png'):
    datas.append(('icon.png', '.'))

a = Analysis(
    ['discord_sender.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Discord_Sender',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
    version='version_info.txt',
)
