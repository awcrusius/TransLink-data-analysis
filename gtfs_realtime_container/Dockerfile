# Use python-slim as base
FROM python:3.14.3-slim

# Install Python packages
RUN pip install --no-cache-dir \
    requests \
    PyYAML \
    gtfs-realtime-bindings \
    numpy  \
    pandas  \
    psycopg2-binary

# Set the working directory in the container
WORKDIR /app

# Add the required files into the container at /app
ADD . /app

# Set Python to run unbuffered to show logs correctly
ENV PYTHONUNBUFFERED=1

# Command to run the Python script
CMD ["python3", "gtfs_realtime_etl.py"]