# AIM runtime image.
#
# GPU/Ollama are intentionally not installed here. Ollama runs in its own
# container, while this image only contains AIM and the deterministic analysis
# tools required by the CLI.
FROM python:3.12-slim-bullseye

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git cmake build-essential pkg-config \
    zstd \
    p7zip-full upx-ucl \
    binutils file libimage-exiftool-perl \
    libboost-regex-dev \
    libboost-program-options-dev \
    libboost-system-dev \
    libboost-filesystem-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install radare2
RUN git clone https://github.com/radareorg/radare2 /opt/radare2 \
    && /opt/radare2/sys/install.sh 

# Create working directory
WORKDIR /app

# Copy requirements and install Python dependencies (cache)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create unprivileged user and writable dirs
RUN groupadd -g 1000 tux \
    && useradd -m -u 1000 -g tux -s /bin/sh tux \
    && mkdir -p /app/output /app/logs /home/tux \
    && chown -R tux:tux /app/output /app/logs /home/tux \
    && chmod +x /app/entrypoint.sh 

# Run as non-root
USER tux

# Entrypoint
ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]
