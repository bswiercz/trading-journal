FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend source code
COPY backend/ ./backend/

# Copy the frontend. It's a single self-contained HTML file (no JS
# build step / no frontend-builder stage needed), so it's copied straight
# in rather than pulled from a build stage.
COPY frontend/ ./frontend/

# Copy requirements.txt and the WSGI entry point
COPY requirements.txt ./requirements.txt
COPY run.py ./run.py

# Install Python dependencies (gunicorn is already pinned in requirements.txt)
RUN pip install --no-cache-dir -r requirements.txt

# Create the directories used at runtime. These are meant to be mounted as
# volumes (see docker-compose.yml) so the database and secrets survive
# container rebuilds and are never baked into the image.
RUN mkdir -p /app/data /app/config

# NOTE: config/config.ini is intentionally NOT copied into the image.
# Generate it with `python scripts/generate_config.py` and mount the
# config/ and data/ directories as volumes at runtime — see README.md.

# Run as a non-root user rather than root inside the container.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV PORT=5000

#backend/ imports itself as a package (e.g. `from backend.config import ...`),
# so the project root — not backend/ — needs to be on the path.
ENV PYTHONPATH=/app
ENV APP_CONFIG_PATH=/app/config/config.ini

# Start with gunicorn WSGI server
CMD gunicorn --workers=4 --worker-class=sync --bind=0.0.0.0:${PORT} --timeout=120 --access-logfile=- --error-logfile=- run:app
