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

# Install radare2
RUN git clone https://github.com/radareorg/radare2 /opt/radare2 \
    && /opt/radare2/sys/install.sh 

# Install r2pipe
RUN pip3 install r2pipe

# # Install Ollama 
# RUN curl -fsSL https://ollama.com/install.sh | sh

# Create working directory
WORKDIR /app

# Copy requirements and install Python dependencies (cache)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files
COPY . .

# Create unprivileged user and writable dirs
RUN groupadd -g 1000 tux \
    && useradd -m -u 1000 -g tux -s /bin/bash tux \
    && mkdir -p /app/output /app/logs /home/tux \
    && chown -R tux:tux /app/output /app/logs /home/tux \
    && chmod +x /app/entrypoint.sh 

# Run as non-root
USER tux

# Entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
