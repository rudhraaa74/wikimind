FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install them
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy all backend code
COPY backend/ ./backend/

# Ensure the logs directory exists
RUN mkdir -p /app/logs

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
