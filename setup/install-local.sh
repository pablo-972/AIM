#!/usr/bin/env bash

# This script sets up AIM Framework
set -eu

# Ensures the script is being run as root
ID=$(id -u)
if [ "0$ID" -ne 0 ]; then
	echo "Please run this script as root"
	exit 0
fi
REAL_USER=${SUDO_USER:-$USER}

# Ensures .env exists and loads it
if [ ! -f ".env" ]; then
    echo "File .env not found."
    echo "Please create .env file as show as example."
    exit 0
else
    source .env
fi


system_update_and_dependencies(){
    echo "Updating and upgrading the system"
    apt update -y && apt upgrade -y

    echo "Installing dependencies"
    apt install -y curl git cmake make g++ zstd \
        python3 python3-venv python3-pip \
        p7zip-full binutils file exiftool upx yara libyara-dev \
        libboost-filesystem-dev libboost-program-options-dev libboost-regex-dev libboost-system-dev libssl-dev   
}


install_ollama_and_model(){
    if command -v ollama &> /dev/null; then
        echo "Ollama already installed"
    else
        read -p "Ollama is not installed. Do you want to install it? (y/n):" confirm
        if [[ $confirm == [yY] ]]; then 
            echo "Installing Ollama"
            curl -fsSL https://ollama.com/install.sh | sh
            sleep 5
        
            read -p "Do you want to install models from OLLAMA_PRELOAD_MODELS? (y/n):" confirm
            if [[ $confirm == [yY] ]]; then
                for model in ${OLLAMA_PRELOAD_MODELS:-}; do
                    echo "Downloading $model"
                    ollama pull "$model"
                done
            fi
        else
            echo "Skipping Ollama instalation"
            return
        fi
    fi
}


system_update_and_dependencies
install_ollama_and_model


echo ""
echo "Setup completed"
echo "Execute framework: python3 main.py -h"
