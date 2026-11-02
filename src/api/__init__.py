from fastapi import FastAPI

def create_app() -> FastAPI:
    app = FastAPI(title="Sonic Brownian API", version="0.1.0")

    #app.include_router()

    return app


app = create_app()