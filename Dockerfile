# Step 1: Use a clean Linux Node environment
FROM node:20-bullseye-slim

# Step 2: Install system tools, Python3, and FFmpeg
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Step 3: Download the absolute newest version of yt-dlp straight into the Linux system
RUN curl -L https://github.com -o /usr/local/bin/yt-dlp \
    && chmod a+rx /usr/local/bin/yt-dlp

# Step 4: Setup our project folder
WORKDIR /app

# Step 5: Copy dependencies and install them
COPY package*.json ./
RUN npm install

# Step 6: Copy your application files
COPY . .

# Step 7: Go!
EXPOSE 3000
CMD ["npm", "start"]
