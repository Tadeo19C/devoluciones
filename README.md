# Control de Devoluciones (React + Flask)

## Backend (Flask)

### Instalación

1. Crear un entorno virtual y activarlo.
2. Instalar dependencias:
   - Archivo: backend/requirements.txt

### Ejecutar

- Ejecuta el servidor con:
  - `python backend/app.py`

### Verificacion rapida de carga CSV/XLSX

- Ejecuta la prueba automatica:
  - `/workspaces/devoluciones/.venv/bin/python backend/smoke_test_upload.py`

Si todo funciona, mostrara:
- `PASS: CSV y XLSX suben, actualizan dashboard y se guardan en SQLite.`

El backend quedará disponible en `http://localhost:5000`.

## Frontend (React + Vite)

### Instalación

- Instala dependencias:
  - Archivo: frontend/package.json

### Ejecutar

- Inicia el frontend con:
  - `npm install`
  - `npm run dev`

El frontend quedará disponible en `http://localhost:5173`.

## Endpoints

- `POST /upload`: recibe un CSV y lo concatena con el maestro.
- `GET /dashboard`: devuelve métricas agregadas.

## Despliegue (gratis)

### Backend (Render)
- Tipo: Web Service
- Root: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn wsgi:app`
- Runtime: `python-3.11.8` (usa `backend/runtime.txt`)

### Frontend (Vercel)
- Root: `frontend`
- Build command: `npm run build`
- Output: `dist`
- Env: `VITE_API_BASE` = URL pública de Render
