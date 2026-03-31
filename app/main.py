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

# Monta el monitor simple pantalls en /monitor-simple-pantallas
app.mount(
    "/monitor-simple-pantallas",
    StaticFiles(directory="app/web/static/monitor_simple_pantallas", html=True),
    name="monitor-simple-pantallas",
)

# Monta la pantalla de moderacion en /moderacion
app.mount(
    "/moderacion",
    StaticFiles(directory="app/web/static/moderacion", html=True),
    name="moderacion",
)

# Monta la pantalla de recinto en /pantalla
app.mount(
    "/pantalla",
    StaticFiles(directory="app/web/static/pantalla", html=True),
    name="pantalla",
)

# Monta la pantalla2 de recinto en /pantalla2
app.mount(
    "/pantalla2",
    StaticFiles(directory="app/web/static/pantalla2", html=True),
    name="pantalla2",
)

# Monta SOLO las imágenes de bancas
app.mount(
    "/bancas",
    StaticFiles(directory="app/web/static/bancas"),
    name="bancas",
)