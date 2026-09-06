FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
COPY pyproject.toml ./
COPY nexuflow_cloud ./nexuflow_cloud
RUN pip install --no-cache-dir .
CMD ["sh", "-c", "uvicorn nexuflow_cloud.main:app --host 0.0.0.0 --port ${PORT}"]
