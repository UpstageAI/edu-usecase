from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import router
from .database import build_database_url, create_engine, create_sessionmaker, initialize_database
from .seed_data import seed_if_empty
from .storage import UploadStorage

STATIC_DIR = Path(__file__).parent / "static"


class SPAStaticFiles(StaticFiles):
    """Serve the React build and fall back to index.html for history navigation."""

    async def get_response(self, path: str, scope):  # type: ignore[override]
        response = await super().get_response(path, scope)
        if response.status_code == 404:
            index_path = Path(self.directory) / "index.html"
            if index_path.exists():
                return FileResponse(index_path)
        return response


def create_app() -> FastAPI:
    app = FastAPI(title="PyPI Upload Demo", version="0.1.4")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    storage = UploadStorage()
    app.state.storage = storage

    database_url = build_database_url(storage.base_directory.parent)
    engine = create_engine(database_url)
    session_factory = create_sessionmaker(engine)
    app.state.db_engine = engine
    app.state.db_sessionmaker = session_factory

    @app.on_event("startup")
    async def _startup() -> None:
        await storage.ensure_ready()
        await initialize_database(engine)
        async with session_factory() as session:
            await seed_if_empty(session)
            await session.commit()

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        await engine.dispose()

    app.include_router(router, prefix="/api", tags=["documents"])

    if STATIC_DIR.exists():
        app.mount("/", SPAStaticFiles(directory=STATIC_DIR, html=True), name="spa")

    return app


app = create_app()
