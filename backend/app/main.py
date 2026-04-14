"""FastAPI application entrypoint."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.config import get_settings
from app.database import dispose_engine
from app.logging_config import setup_logging
from app.middleware.error_handler import register_error_handlers
from app.middleware.request_id import RequestIDMiddleware
from app.routers import (
    attributes,
    auth,
    categories,
    dashboard,
    export,
    health,
    images,
    products,
    users,
)
from app.routers import import_ as import_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    logger.info(
        "app_startup",
        environment=settings.environment,
        port=settings.port,
    )
    # Touch dirs so they exist for uploads/imports.
    _ = settings.upload_path
    _ = settings.inbox_path
    yield
    logger.info("app_shutdown")
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="DataPIM API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Request ID first so all downstream logs carry it.
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    register_error_handlers(app)

    os.makedirs(settings.upload_dir, exist_ok=True)
    app.mount(
        "/uploads",
        StaticFiles(directory=settings.upload_dir),
        name="uploads",
    )

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(users.router, prefix="/api/users", tags=["users"])
    app.include_router(categories.router, prefix="/api/categories", tags=["categories"])
    app.include_router(products.router, prefix="/api/products", tags=["products"])
    app.include_router(attributes.router, tags=["attributes"])
    app.include_router(images.router, tags=["images"])
    app.include_router(import_router.router, prefix="/api/import", tags=["import"])
    app.include_router(export.router, tags=["export"])
    app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
    return app


app = create_app()
