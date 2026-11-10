# ---- frontend build ----
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- backend runtime (serves API + built frontend) ----
FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml ./
COPY backend ./backend
RUN pip install --no-cache-dir -e .

COPY --from=frontend /build/dist ./frontend/dist

EXPOSE 10000
CMD ["uvicorn", "app.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "10000", "--app-dir", "backend"]
