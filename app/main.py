from fastapi import FastAPI

from app.api import crawl, health, prices, quote, scaffold_bids


def create_app() -> FastAPI:
    app = FastAPI(title="building-price-intel", version="0.1.0")
    app.include_router(health.router)
    app.include_router(prices.router)
    app.include_router(scaffold_bids.router)
    app.include_router(quote.router)
    app.include_router(crawl.router)
    return app


app = create_app()
