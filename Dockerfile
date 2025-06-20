# Dockerfile
FROM python:3.11-slim

# 1) Instala qpdf (per PyHanko) i neteja cache d'apt
RUN apt-get update \
 && apt-get install -y qpdf \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2) Copia el requirements i instala-ho (incloent gunicorn)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn==20.1.0

# 3) Copia el codi de l'aplicació
COPY app/ ./app

# 4) Crea un usuari no-root i passa a ser-lo
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# 5) Engega amb gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app.app:app", "--workers=4", "--timeout=120"]

