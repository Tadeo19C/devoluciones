# Control de Devoluciones (React + Flask)

## Backend (Flask)

### Instalación

1. Crear un entorno virtual y activarlo.
2. Instalar dependencias:
   - Archivo: backend/requirements.txt

### Ejecutar

- Ejecuta el servidor con:
  - `python backend/app.py`

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
