"""Production entry point for PyInstaller packaging."""
import os
import sys
from pathlib import Path


def get_resource_path(relative_path: str) -> Path:
    """Get path to resource, works for both dev and PyInstaller bundle."""
    if getattr(sys, '_MEIPASS', None):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).parent / relative_path


if __name__ == "__main__":
    base = Path(sys._MEIPASS) if getattr(sys, '_MEIPASS', None) else Path(__file__).parent.parent
    sys.path.insert(0, str(base))

    os.environ.setdefault("FILEAI_CONFIG", str(get_resource_path("config.yaml")))

    env_file = get_resource_path(".env")
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)

    import uvicorn
    from backend.main import app

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info",
    )
