FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
LABEL org.opencontainers.image.title="PetDiary" org.opencontainers.image.version="0.0.1" org.opencontainers.image.source="https://github.com/Skoun181/PetDiary"
RUN groupadd --gid 10001 petdiary && useradd --uid 10001 --gid 10001 --no-create-home petdiary && mkdir -p /data && chown 10001:10001 /data
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py catalog.py reset_password.py VERSION ./
COPY templates ./templates
COPY static ./static
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3).close()"
CMD ["gunicorn","--bind=0.0.0.0:8080","--workers=1","--threads=2","--timeout=60","--worker-tmp-dir=/tmp","--access-logfile=-","--access-logformat=%(s)s %(L)s","app:create_app()"]
