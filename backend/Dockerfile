FROM python:3.11-slim

# Create directory for app
WORKDIR /app

# Install system dependencies (if any)
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY backend/requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy any entrypoint scripts if needed (optional)
# COPY entrypoint.sh /app/
# RUN chmod +x /app/entrypoint.sh

# We'll rely on volume mounting for the source code in development
# ENTRYPOINT ["/app/entrypoint.sh"]  # If you have migrations or setup steps

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
