# Use pre-built base image with dependencies from Docker Hub
ARG BASE_IMAGE=rootlyio/on-call-health:backend-base
FROM ${BASE_IMAGE}

WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .

# Install any new dependencies not in base image
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install any new dependencies (like arq) not in base image
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8000

# Set up startup script permissions
RUN chmod +x start.sh

# Command to run migrations and start the application
CMD ["./start.sh"]
