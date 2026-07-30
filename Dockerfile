# Step 1: Use an official Linux image that has Node.js pre-installed
FROM node:20-bullseye-slim

# Step 2: Install Python3 and FFmpeg directly onto the system
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Step 3: Set up your application directory
WORKDIR /app

# Step 4: Copy dependency lists and install them
COPY package*.json ./
RUN npm install

# Step 5: Copy the rest of your project files
COPY . .

# Step 6: Expose the network port and start the backend engine
EXPOSE 3000
CMD ["npm", "start"]
