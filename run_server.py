#!/usr/bin/env python3
"""Entry point to run the backend server."""
import os
from dotenv import load_dotenv
import uvicorn

load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"))

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
