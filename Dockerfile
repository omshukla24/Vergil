FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose the port Cloud Run uses
EXPOSE 8080

# Run the FastAPI app on the port specified by the PORT runtime environment variable
CMD ["sh", "-c", "uvicorn vergil_engine.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
