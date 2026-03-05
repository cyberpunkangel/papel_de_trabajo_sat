# Contribuciones

Las contribuciones son bienvenidas.

## Flujo recomendado

1. Crea una rama desde `main`.
2. Realiza cambios pequeños y enfocados.
3. Verifica que la app arranque correctamente.
4. Envía un Pull Request con descripción clara.

## Entorno local

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecutar la app

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Buenas prácticas

- No incluir datos sensibles (RFC, contraseñas, llaves/certificados) en commits.
- Mantener cambios consistentes con el estilo actual del proyecto.
- Documentar cualquier cambio funcional relevante.

## Reporte de bugs

Incluye siempre:

- Pasos para reproducir.
- Resultado esperado vs resultado actual.
- Logs o trazas relevantes (sin datos sensibles).
