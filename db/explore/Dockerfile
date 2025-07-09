FROM python:3.11-slim

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire package
COPY . .

# Install the package
RUN pip install -e .

# Create output directory
RUN mkdir -p /output

# Run the script
ENTRYPOINT ["python", "/app/run.py"]