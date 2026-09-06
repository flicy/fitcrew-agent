from fastapi import FastAPI

from bodyos_api import __version__
from bodyos_api.bodyos_routes import router as bodyos_router
from bodyos_api.health_routes import router as health_router
from bodyos_api.owner_routes import router as owner_router
from bodyos_api.pairing_routes import router as pairing_router
from bodyos_api.product_routes import router as product_router
from bodyos_api.public_auth import router as public_auth_router


def create_app() -> FastAPI:
    app = FastAPI(title="FitCrew BodyOS API", version=__version__)
    app.include_router(health_router)
    app.include_router(owner_router)
    app.include_router(pairing_router)
    app.include_router(bodyos_router)
    app.include_router(product_router)
    app.include_router(public_auth_router)

    @app.get("/healthz", tags=["operations"])
    def healthcheck() -> dict[str, str]:
        return {"status": "ok", "version": f"v{__version__}"}

    return app


app = create_app()
