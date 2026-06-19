FROM python:3.11-alpine

# Unbuffered stdout so logs appear live in `docker logs` / the terminal (Python block-buffers
# when stdout is a pipe, which otherwise makes the device look silent).
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Python dependency: paho-mqtt for the firetest TestFlag/TC path (pure-Python, no build deps).
RUN pip install --no-cache-dir paho-mqtt==1.6.1

# Application code (dispatcher + both test types). config.json is NOT baked in — it holds the
# broker password and is mounted at runtime (docker run -v .../config.json:/app/config.json:ro)
# so the image stays secret-free and reusable.
COPY entrypoint.py /app/
COPY firetest/ /app/firetest/
COPY jetson/ /app/jetson/

# Dispatch to the chosen test type (firetest | jetson) at boot.
CMD ["python", "entrypoint.py"]
