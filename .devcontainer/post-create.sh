#!/bin/bash

echo "🚀 Setting up LangExtract development environment..."

# Create necessary directories
mkdir -p output data/sample_texts

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📝 Created .env file from .env.example"
    echo "⚠️  Please add your LANGEXTRACT_API_KEY to .env"
fi

# Install pre-commit hooks if available
if [ -f .pre-commit-config.yaml ]; then
    pre-commit install
fi

# Download sample data if needed
if [ ! -f data/sample_texts/shakespeare.txt ]; then
    echo "📥 Downloading sample texts..."
    curl -s https://www.gutenberg.org/files/1513/1513-0.txt -o data/sample_texts/shakespeare.txt
fi

echo "✅ Development environment setup complete!"
echo "📖 Run 'python examples/basic_extraction.py' to test the setup"