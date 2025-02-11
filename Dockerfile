FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create directory for SQLite database
RUN mkdir -p /app/data
VOLUME /app/data

# Expose port for admin interface
EXPOSE 5000

CMD ["python", "bot.py"]