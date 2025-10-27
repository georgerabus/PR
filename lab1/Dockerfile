FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy the server script
COPY server.py .

# Expose port 8000
EXPOSE 8000

# Default command (can be overridden in docker-compose.yml)
CMD ["python", "server.py", "/content"]
