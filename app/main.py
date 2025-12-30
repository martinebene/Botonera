from fastapi import FastAPI

from app.api.routes import sesiones, entradas, votaciones

app = FastAPI(title="API Concejo Deliberante")

app.include_router(sesiones.router)
app.include_router(entradas.router)
app.include_router(votaciones.router)
