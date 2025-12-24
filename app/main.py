from fastapi import FastAPI

from app.api.routes import sesiones

app = FastAPI(
    title="API Concejo Deliberante (memoria, sin DB)",
    version="0.1.0",
)


@app.get("/")
def root():
    """
    Endpoint simple de prueba.
    """
    return {"mensaje": "API Concejo funcionando (memoria, sin DB)"}


# Registramos el router de sesiones
app.include_router(sesiones.router, prefix="/sesiones", tags=["Sesiones"])
