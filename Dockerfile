# Step 1: Use an efficient official Python framework base image
FROM python:3.11-slim

# Step 2: Install system tools and FFmpeg for video processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Step 3: Set up active workspace path
WORKDIR /app

# Step 4: Install package requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Transfer app files
COPY . .

# Step 6: Bind system port and invoke high-performance Uvicorn server production app
EXPOSE 3000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000"]
