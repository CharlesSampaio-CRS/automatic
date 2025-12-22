#!/usr/bin/env python3
"""
FastAPI Application Entry Point
"""
import uvicorn
import os

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "fastapi_app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
