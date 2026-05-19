from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import attachments, crawl, crawl_orchestrator, health, managed_browser, notifications, prices, quote, scaffold_bids, source_library

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def create_app() -> FastAPI:
    app = FastAPI(title="building-price-intel", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(prices.router)
    app.include_router(scaffold_bids.router)
    app.include_router(quote.router)
    app.include_router(crawl.router)
    app.include_router(notifications.router)
    app.include_router(attachments.router)
    app.include_router(managed_browser.router)
    app.include_router(source_library.router)
    app.include_router(crawl_orchestrator.router)
    return app


app = create_app()
