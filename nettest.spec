# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.building.build_main import Analysis, PYZ, EXE
from PyInstaller.utils.hooks import collect_all
import customtkinter
import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'dns',
        'dns.resolver',
        'rich',
        'rich.logging',
        'rich.console',
        'customtkinter',
        'PIL',
        'PIL._imagingtk',
        'PIL._tkinter_finder',
        'aiohttp',
        'aiofiles',
        'httpx',
        'h2',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Include customtkinter assets (themes, fonts)
ctk_path = os.path.dirname(customtkinter.__file__)
for root, dirs, files in os.walk(ctk_path):
    for file in files:
        full = os.path.join(root, file)
        rel = os.path.relpath(full, ctk_path)
        a.datas.append((os.path.join("customtkinter", rel), full, "DATA"))

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='nettest',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
