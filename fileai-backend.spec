# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['backend/app_entry.py'],
    pathex=['.'],
    binaries=[],
    datas=[('backend/config.yaml', 'backend'), ('backend/.env', 'backend')],
    hiddenimports=['backend.services.scanner', 'backend.services.classifier', 'backend.services.rule_engine', 'backend.services.organizer', 'backend.services.history', 'backend.services.watcher', 'dotenv', 'backend.config', 'backend.models'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='fileai-backend',
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
