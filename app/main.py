from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import moderacion, estados, entradas

app = FastAPI(title="API Concejo Deliberante")


app.include_router(moderacion.router)
app.include_router(estados.router)
app.include_router(entradas.router)



# Monta el monitor simple en /monitor-simple
app.mount(
    "/monitor-simple",
    StaticFiles(directory="app/web/static/monitor_simple", html=True),
    name="monitor-simple",
)