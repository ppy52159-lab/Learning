# 1. Use an official lightweight Python image
FROM python:3.11-slim

# 2. Prevent Python from writing .pyc files & enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Set working directory inside the container
WORKDIR /app

# 4. Install dependencies first (leveraging Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy application code into the container
COPY . .

# 6. Expose internal port 8000
EXPOSE 8000

# 7. Start Gunicorn with Uvicorn workers on container boot
CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
