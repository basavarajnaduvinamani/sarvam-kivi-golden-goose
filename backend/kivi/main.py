from .app import app
from frontend.router import router as frontend_router
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.include_router(frontend_router)

__all__ = ["app"]
