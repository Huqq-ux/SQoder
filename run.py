import sys

if sys.platform == "win32":
    import asyncio as _asyncio
    _asyncio.set_event_loop_policy(_asyncio.WindowsSelectorEventLoopPolicy())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "Coder.server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
