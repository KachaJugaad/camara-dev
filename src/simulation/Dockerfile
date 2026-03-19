FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer cache)
COPY src/simulation/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy carrier configs and source
COPY config/ ./config/
COPY src/simulation/app/ ./src/simulation/app/

WORKDIR /app/src/simulation/app
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "info"]
