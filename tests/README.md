# Pruebas de caracterizacion

Ejecutar desde la raiz del repositorio, luego de instalar `requirements-backend.txt`:

```powershell
python -m pytest -q
python -m pytest -q tests/unit
python -m pytest -q tests/integration
```

Las fixtures aislan los singletons de sesion, votacion y pantallas, los IDs en memoria y el buffer de logs. Los concejales usados por las pruebas son ficticios y los logs se escriben en directorios temporales de pytest.
