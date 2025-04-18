
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/data && chmod -R 777 /app/data
ENV DATABASE_PATH=/app/data/rental.db
EXPOSE 5000
CMD ["python", "app.py"]
