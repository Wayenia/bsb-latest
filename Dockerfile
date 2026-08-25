FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libglib2.0-0 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt ./

RUN pip install --no-cache-dir --upgrade pip setuptools \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/entrypoint.sh

# Execution sans privileges : par defaut un conteneur tourne en root, si bien
# qu'une execution de code arbitraire dans l'application ecrirait en root dans
# le projet monte depuis l'hote. `media`, `staticfiles` et `logs` sont montes
# en volume et doivent appartenir a l'utilisateur applicatif pour rester
# inscriptibles.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/media /app/staticfiles /app/logs \
    && chown -R appuser:appuser /app

USER appuser

CMD ["./entrypoint.sh"]