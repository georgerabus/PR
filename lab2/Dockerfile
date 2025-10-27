FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Copy all server/client/testing code into the image
COPY server_single.py .
COPY server_threaded.py .
COPY load_test.py .

# (no extra deps needed; all stdlib)

EXPOSE 8080
EXPOSE 8081

# We won't set a single fixed CMD here, because in docker-compose we’ll
# choose the command per service (single, threaded, tester).
CMD ["python", "server_single.py", "/srv/content", "--port", "8080"]
