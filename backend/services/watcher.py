"""Watcher — monitors directories for new files using watchdog."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Callable, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from backend.config import get_config

logger = logging.getLogger(__name__)


class _NewFileHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback

    def on_created(self, event):
        if isinstance(event, FileCreatedEvent) and not event.is_directory:
            name = Path(event.src_path).name
            if not name.startswith("."):
                logger.info(f"New file detected: {event.src_path}")
                self.callback(event.src_path)


class DirectoryWatcher:
    def __init__(self):
        self._observer: Optional[Observer] = None
        self._callbacks: list[Callable[[str], None]] = []
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def on_new_file(self, callback: Callable[[str], None]):
        self._callbacks.append(callback)

    def _dispatch(self, path: str):
        for cb in self._callbacks:
            try:
                cb(path)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def start(self):
        if self._running:
            return

        config = get_config()
        self._observer = Observer()
        handler = _NewFileHandler(self._dispatch)

        for d in config.get_watch_dirs():
            if d.exists():
                self._observer.schedule(handler, str(d), recursive=False)
                logger.info(f"Watching: {d}")

        self._observer.start()
        self._running = True
        logger.info("Directory watcher started")

    def stop(self):
        if self._observer and self._running:
            self._observer.stop()
            self._observer.join()
            self._running = False
            logger.info("Directory watcher stopped")


watcher = DirectoryWatcher()
