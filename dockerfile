# Base image GPU-ready
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git cmake build-essential \
    python3 python3-pip \
    zstd \
    p7zip-full upx \
    binutils file exiftool \
    libboost-regex-dev \
    libboost-program-options-dev \
    libboost-system-dev \
    libboost-filesystem-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*


# Create working directory
WORKDIR /app

# Copy requirements and install Python dependencies (cache)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files
COPY . .

# Install radare2
RUN git clone https://github.com/radareorg/radare2 /opt/radare2 \
    && /opt/radare2/sys/install.sh 

# Install r2pipe
RUN pip3 install r2pipe

# # Install Ollama 
# RUN curl -fsSL https://ollama.com/install.sh | sh

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
