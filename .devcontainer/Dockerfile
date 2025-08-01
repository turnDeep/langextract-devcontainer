FROM mcr.microsoft.com/devcontainers/python:3.11-bullseye

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Install Ollama (for local LLM support)
RUN curl -fsSL https://ollama.com/install.sh | sh

# Set up Python environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install Python development tools
RUN pip install --upgrade pip setuptools wheel

# Create workspace directory
WORKDIR /workspace

# Copy requirements first for better caching
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# Install additional development tools
RUN pip install \
    black \
    pylint \
    ipython \
    jupyter \
    notebook

# Create directories for output
RUN mkdir -p /workspace/output /workspace/data

# Switch to non-root user
USER $USERNAME

# Set up Jupyter
RUN jupyter notebook --generate-config