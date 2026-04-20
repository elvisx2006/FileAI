"""FastAPI application — REST + WebSocket endpoints for the file organizer."""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path)

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from backend.config import load_config, get_config, save_app_config
from backend.models import ClassifyResult, FileInfo, OrganizePlan
from backend.services import scanner, classifier, rule_engine, organizer, history, icloud
from backend.services.watcher import watcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Stores active WebSocket connections
ws_clients: list[WebSocket] = []
# In-memory plan store (keyed by plan id)
plan_store: dict[str, OrganizePlan] = {}
# Track ongoing organize tasks: plan_id -> {current, total, done, result}
organize_status: dict[str, dict] = {}

# Main event loop (set in lifespan) — watcher callbacks run on watchdog threads
_main_loop: asyncio.AbstractEventLoop | None = None


async def broadcast(event: dict):
    data = json.dumps(event, ensure_ascii=False)
    disconnected = []
    for ws in ws_clients:
        try:
            await ws.send_text(data)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        ws_clients.remove(ws)


def _on_new_file(path: str):
    """Called by the watcher when a new file appears."""
    if _main_loop is None:
        return
    try:
        asyncio.run_coroutine_threadsafe(
            broadcast({"type": "new_file", "path": path}),
            _main_loop,
        )
    except Exception as e:
        logger.warning("Could not schedule new_file broadcast: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _main_loop
    load_config()
    await history.init_db()
    _main_loop = asyncio.get_running_loop()
    watcher.on_new_file(_on_new_file)
    logger.info("Backend started")
    try:
        yield
    finally:
        _main_loop = None
        watcher.stop()
        logger.info("Backend stopped")


app = FastAPI(title="File Organizer API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ──────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ── Scan ────────────────────────────────────────────────

@app.get("/api/scan")
async def scan_all():
    results = scanner.scan_all_watched()
    return {
        "directories": [r.dict() for r in results],
        "total_files": sum(r.total_count for r in results),
        "total_size": sum(r.total_size for r in results),
    }


@app.get("/api/scan/{dir_name}")
async def scan_one(dir_name: str):
    config = get_config()
    target = None
    for d in config.get_watch_dirs():
        if d.name.lower() == dir_name.lower():
            target = d
            break
    if target is None:
        return {"error": f"Directory '{dir_name}' is not in watch list"}
    result = scanner.scan_directory(str(target))
    return result.dict()


# ── Classify ────────────────────────────────────────────

@app.post("/api/classify")
async def classify_files(files: list[dict]):
    file_infos = [FileInfo(**f) for f in files]

    rule_results, needs_ai = rule_engine.classify_batch_by_rules(file_infos)

    total_files = len(file_infos)
    rule_done = len(rule_results)

    await broadcast({
        "type": "classify_progress",
        "current": rule_done,
        "total": total_files,
        "stage": "rule",
    })

    ai_results = []
    if needs_ai:
        loop = asyncio.get_running_loop()

        def on_ai_progress(current: int, total: int):
            try:
                loop.call_soon_threadsafe(
                    loop.create_task,
                    broadcast({
                        "type": "classify_progress",
                        "current": rule_done + current,
                        "total": total_files,
                        "stage": "ai",
                    }),
                )
            except Exception:
                pass

        ai_results = await loop.run_in_executor(
            None, lambda: classifier.classify_batch(needs_ai, on_progress=on_ai_progress)
        )

    all_results = rule_results + ai_results
    plan = organizer.build_plan(all_results, dry_run=True)
    plan_store[plan.id] = plan

    await broadcast({
        "type": "classify_progress",
        "current": total_files,
        "total": total_files,
        "stage": "done",
    })

    return {
        "plan_id": plan.id,
        "total": len(all_results),
        "rule_classified": len(rule_results),
        "ai_classified": len(ai_results),
        "items": [r.dict() for r in all_results],
    }


# ── Organize ───────────────────────────────────────────

@app.post("/api/organize/preview")
async def organize_preview(files: list[dict]):
    """Scan + classify + return preview without moving anything."""
    file_infos = [FileInfo(**f) for f in files]
    rule_results, needs_ai = rule_engine.classify_batch_by_rules(file_infos)

    ai_results = []
    if needs_ai:
        ai_results = classifier.classify_batch(needs_ai)

    all_results = rule_results + ai_results
    plan = organizer.build_plan(all_results, dry_run=True)
    plan_store[plan.id] = plan

    return {
        "plan_id": plan.id,
        "items": [r.dict() for r in all_results],
    }


@app.post("/api/organize/confirm/{plan_id}")
async def organize_confirm(plan_id: str):
    plan = plan_store.get(plan_id)
    if plan is None:
        return {"success": False, "error": "Plan not found or expired", "error_detail": "分类计划已过期（可能后端重启过），请重新扫描并分类。"}

    plan.dry_run = False
    del plan_store[plan_id]
    total_items = len(plan.items)

    organize_status[plan_id] = {"current": 0, "total": total_items, "done": False, "result": None}

    loop = asyncio.get_running_loop()

    async def _run_organize():
        def on_progress(current: int, total: int, file_name: str):
            organize_status[plan_id]["current"] = current
            asyncio.run_coroutine_threadsafe(
                broadcast({
                    "type": "organize_progress",
                    "current": current,
                    "total": total,
                    "file_name": file_name,
                }),
                loop,
            )

        try:
            result = await loop.run_in_executor(
                None, lambda: organizer.execute_plan(plan, on_progress=on_progress)
            )
        except Exception as e:
            logger.error(f"execute_plan crashed: {e}", exc_info=True)
            organize_status[plan_id]["done"] = True
            organize_status[plan_id]["result"] = {"error": f"{type(e).__name__}: {e}"}
            await broadcast({
                "type": "organize_error",
                "plan_id": plan_id,
                "error": f"{type(e).__name__}: {e}",
            })
            return

        records = result["records"]
        errors = result["errors"]
        skipped = result["skipped"]

        if records:
            await history.save_records(records)

        done_payload = {
            "type": "organize_done",
            "plan_id": plan_id,
            "moved": len(records),
            "skipped": skipped,
            "failed": len(errors),
            "errors": [{"file": e["file"], "error": e["error"]} for e in errors],
            "empty_dirs_removed": result.get("empty_dirs_removed", 0),
        }
        organize_status[plan_id]["done"] = True
        organize_status[plan_id]["result"] = done_payload
        organize_status[plan_id]["current"] = total_items
        await broadcast(done_payload)

    asyncio.create_task(_run_organize())

    return {
        "success": True,
        "async": True,
        "message": f"开始移动 {total_items} 个文件",
        "total": total_items,
        "plan_id": plan_id,
    }


@app.get("/api/organize/status/{plan_id}")
async def organize_status_check(plan_id: str):
    """Poll-based fallback to check organize progress when WebSocket is unavailable."""
    status = organize_status.get(plan_id)
    if status is None:
        return {"found": False}
    return {
        "found": True,
        "current": status["current"],
        "total": status["total"],
        "done": status["done"],
        "result": status["result"],
    }


# ── Quick organize (scan → classify → execute in one call) ──

@app.post("/api/organize/quick")
async def quick_organize(
    dir_name: Optional[str] = Query(None),
    dry_run: bool = Query(True),
):
    config = get_config()
    if dir_name:
        target = None
        for d in config.get_watch_dirs():
            if d.name.lower() == dir_name.lower():
                target = d
                break
        if target is None:
            return {"error": f"Directory '{dir_name}' not found"}
        scan_results = [scanner.scan_directory(str(target))]
    else:
        scan_results = scanner.scan_all_watched()

    all_files = []
    for sr in scan_results:
        all_files.extend(sr.files)

    if not all_files:
        return {"message": "No files to organize", "moved": 0}

    rule_results, needs_ai = rule_engine.classify_batch_by_rules(all_files)
    ai_results = classifier.classify_batch(needs_ai) if needs_ai else []
    all_results = rule_results + ai_results

    plan = organizer.build_plan(all_results, dry_run=dry_run)

    if not dry_run:
        result = organizer.execute_plan(plan)
        records = result["records"]
        if records:
            await history.save_records(records)
        return {
            "success": len(result["errors"]) == 0,
            "moved": len(records),
            "failed": len(result["errors"]),
            "errors": result["errors"],
            "records": [r.dict() for r in records],
            "empty_dirs_removed": result.get("empty_dirs_removed", 0),
        }
    else:
        plan_store[plan.id] = plan
        return {
            "plan_id": plan.id,
            "dry_run": True,
            "items": [r.dict() for r in all_results],
        }


# ── Undo ────────────────────────────────────────────────

@app.post("/api/undo/{operation_id}")
async def undo(operation_id: str):
    record = await history.get_record(operation_id)
    if record is None:
        return {"error": "Operation not found"}
    if record.undone:
        return {"error": "Already undone"}

    success = organizer.undo_operation(record)
    if success:
        await history.mark_undone(operation_id)
        await broadcast({"type": "undo", "operation_id": operation_id})
        return {"success": True}
    return {"error": "File not found at destination"}


# ── History ─────────────────────────────────────────────

@app.get("/api/history")
async def get_history(page: int = 1):
    records = await history.get_history(page)
    return {"page": page, "records": [r.dict() for r in records]}


# ── Stats ───────────────────────────────────────────────

@app.get("/api/stats")
async def get_stats():
    config = get_config()
    db_stats = await history.get_stats()

    watch_status = {}
    for d in config.get_watch_dirs():
        if d.exists():
            count = sum(1 for f in d.iterdir() if f.is_file() and not f.name.startswith("."))
            watch_status[d.name] = count
        else:
            watch_status[d.name] = 0

    recent = await history.get_history(page=1, page_size=10)

    return {
        "total_operations": db_stats["total_operations"],
        "category_distribution": db_stats["category_distribution"],
        "watch_dirs": watch_status,
        "recent_operations": [r.dict() for r in recent],
    }


# ── Watcher control ────────────────────────────────────

@app.post("/api/watcher/start")
async def start_watcher():
    if watcher.is_running:
        return {"status": "already_running"}
    watcher.start()
    return {"status": "started"}


@app.post("/api/watcher/stop")
async def stop_watcher():
    if not watcher.is_running:
        return {"status": "already_stopped"}
    watcher.stop()
    return {"status": "stopped"}


@app.get("/api/watcher/status")
async def watcher_status():
    return {"running": watcher.is_running}


# ── Config ──────────────────────────────────────────────

@app.get("/api/config")
async def get_current_config():
    config = get_config()
    return config.dict()


class ScanPatchBody(BaseModel):
    max_depth: Optional[int] = None
    skip_project_dirs: Optional[bool] = None
    cleanup_empty_dirs: Optional[bool] = None


class ConfigPatchBody(BaseModel):
    watch_directories: Optional[list[str]] = None
    organize_base: Optional[str] = None
    scan: Optional[ScanPatchBody] = None


@app.patch("/api/config")
async def patch_config(body: ConfigPatchBody):
    kwargs: dict = {}
    if body.watch_directories is not None:
        dirs = [d.strip() for d in body.watch_directories if d and str(d).strip()]
        if not dirs:
            raise HTTPException(status_code=400, detail="watch_directories 不能为空")
        kwargs["watch_directories"] = dirs
    if body.organize_base is not None:
        ob = body.organize_base.strip()
        if not ob:
            raise HTTPException(status_code=400, detail="organize_base 不能为空")
        kwargs["organize_base"] = ob
    if body.scan is not None:
        patch = body.scan.model_dump(exclude_none=True)
        if patch.get("max_depth") is not None and patch["max_depth"] < -1:
            raise HTTPException(status_code=400, detail="scan.max_depth 必须 >= -1")
        kwargs["scan"] = patch
    if not kwargs:
        return {"ok": True, "config": get_config().dict()}
    cfg = save_app_config(**kwargs)
    return {"ok": True, "config": cfg.dict()}


@app.get("/api/icloud/discover")
async def icloud_discover():
    import sys

    root = icloud.icloud_drive_root()
    return {
        "platform": sys.platform,
        "icloud_drive": {
            "path": str(root),
            "exists": root.exists(),
            "recommended_watch_path": "~/Library/Mobile Documents/com~apple~CloudDocs",
        },
        "materialize_supported": sys.platform == "darwin",
        "note": None
        if sys.platform == "darwin"
        else "占位符下载（brctl）仅在 macOS 上可用；可将 iCloud 盘符路径加入监控目录作为兜底。",
    }


# ── Open in Finder ──────────────────────────────────────

@app.post("/api/open-folder")
async def open_folder(body: dict):
    """Open a folder in the system file manager (cross-platform)."""
    import subprocess
    import sys
    folder = body.get("path", "")
    config = get_config()

    shortcuts = {
        "organized": str(config.get_organize_base()),
        "downloads": str(Path.home() / "Downloads"),
        "desktop": str(Path.home() / "Desktop"),
        "documents": str(Path.home() / "Documents"),
        "icloud": str(icloud.icloud_drive_root()),
        "iclouddrive": str(icloud.icloud_drive_root()),
    }

    resolved = shortcuts.get(folder.lower(), folder)

    if resolved.startswith("~/"):
        resolved = str(Path(resolved).expanduser())

    target = Path(resolved)
    if not target.exists():
        target.mkdir(parents=True, exist_ok=True)

    if sys.platform == "win32":
        subprocess.Popen(["explorer", str(target)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(target)])
    else:
        subprocess.Popen(["xdg-open", str(target)])

    return {"success": True, "path": str(target)}


@app.get("/api/organized-tree")
async def get_organized_tree():
    """Return the folder structure under ~/Organized with file counts."""
    config = get_config()
    base = config.get_organize_base()
    if not base.exists():
        return {"base": str(base), "folders": []}

    folders = []
    for item in sorted(base.rglob("*")):
        if item.is_dir():
            rel = str(item.relative_to(base))
            file_count = sum(1 for f in item.iterdir() if f.is_file())
            if file_count > 0:
                folders.append({
                    "path": str(item),
                    "relative": rel,
                    "count": file_count,
                })

    return {"base": str(base), "folders": folders}


# ── WebSocket ───────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        if websocket in ws_clients:
            ws_clients.remove(websocket)


# ── Serve frontend static files ────────────────────────

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="static-assets")

    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        file_path = _frontend_dist / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_frontend_dist / "index.html"))
