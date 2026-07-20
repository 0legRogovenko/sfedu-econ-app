FROM python:3.12-slim

WORKDIR /app

# ca-certificates нужен truststore для нативной проверки TLS
# (парсер sfedu.ru ходит по https)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Непривилегированный пользователь: контейнер, смотрящий в интернет, не должен
# работать от root. Импорт пишет только во временные файлы (/tmp), исходники
# читаются — этих прав достаточно.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

# Healthcheck без curl (в slim-образе его нет): дёргаем /health питоном.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=4).status==200 else 1)"

CMD ["sh", "-c", "alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8000"]
