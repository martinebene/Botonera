from fastapi import FastAPI

from app.api.routes import sesiones, entradas

app = FastAPI(title="API Concejo Deliberante")

# Rutas de sesiones
app.include_router(sesiones.router)

# Rutas de entradas desde los dispositivos físicos
app.include_router(entradas.router)
