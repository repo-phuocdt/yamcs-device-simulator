FROM python:3.11-alpine

WORKDIR /app

# Copy application source code and temporary config into the image
COPY setup_and_run.py /app/
COPY config.json /app/

# Set the default boot execution command
CMD ["python", "setup_and_run.py"]