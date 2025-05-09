# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY Pipfile Pipfile.lock /app/

# Install Python dependencies
RUN pip install pipenv && pipenv install --system --deploy

# Create vector store directory
RUN mkdir -p /app/vector_store

# Copy the current directory contents into the container at /app
COPY . /app

# Make port 8002 available
EXPOSE 8002

# Set Python path
ENV PYTHONPATH=/app
ENV USER_AGENT="Edd"

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]