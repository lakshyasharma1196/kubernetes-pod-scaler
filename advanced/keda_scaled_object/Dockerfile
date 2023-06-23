# Use the official Python image as the base image
FROM python:3.9-slim

# Copy the Python script to the container
COPY scale.py /scale.py

# Install the required Python dependencies
RUN pip install kubernetes

# Set the entrypoint command to run the Python script
CMD ["python", "scale.py"]

