FROM python:3.9-slim

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Install additional production dependencies
RUN pip install --no-cache-dir redis flask-socketio flask-limiter eventlet

# Copy the rest of the application
COPY . .

# Expose the Flask port
EXPOSE 5050

# Run the app with Eventlet for SocketIO
CMD ["python", "app.py"]
