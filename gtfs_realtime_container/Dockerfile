# Use python-slim as base
FROM python:3.14.3-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    libpq-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \
    duckdb \
    requests \
    PyYAML \
    gtfs-realtime-bindings \
    pandas  \
    psycopg2-binary  \
    timescale-vector

# Set the working directory in the container
WORKDIR /app

# Add the required files into the container at /app
ADD . /app

# Set Python to run unbuffered to show logs correctly
ENV PYTHONUNBUFFERED=1

# Command to run the Python script
CMD ["python3", "gtfs_realtime_etl.py"]