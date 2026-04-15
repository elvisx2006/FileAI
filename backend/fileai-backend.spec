# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['../run_server.py'],
    pathex=[],
    binaries=[],
    datas=[('backend/config.yaml', 'backend'), ('backend/.env', 'backend')],
    hiddenimports=['uvicorn.logging', 'uvicorn.lifespan', 'uvicorn.lifespan.on', 'uvicorn.lifespan.off', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.http.h11_impl', 'uvicorn.protocols.http.httptools_impl', 'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto', 'uvicorn.protocols.websockets.wsproto_impl', 'uvicorn.protocols.websockets.websockets_impl', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.loops.asyncio', 'aiosqlite', 'watchdog', 'watchdog.observers', 'watchdog.events', 'yaml', 'dotenv', 'openai', 'backend', 'backend.config', 'backend.models', 'backend.main', 'backend.services', 'backend.services.scanner', 'backend.services.classifier', 'backend.services.rule_engine', 'backend.services.organizer', 'backend.services.history', 'backend.services.watcher'],
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
