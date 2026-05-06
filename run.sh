#!/bin/bash

echo "Starting Blog Post Generator in development mode..."

# Check if virtual environment exists
if [ ! -d "ENVIRONMENT" ]; then
    echo "Creating virtual environment..."
    python3 -m venv ENVIRONMENT
fi

# Activate virtual environment
source ENVIRONMENT/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Download NLTK data if not already downloaded
echo "Checking NLTK data..."
python -m nltk.downloader punkt averaged_perceptron_tagger maxent_ne_chunker words stopwords

# Check for .env file
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found"
    echo "Copying .env.example to .env..."
    cp .env.example .env
    echo "Please edit .env with your credentials before continuing"
    read -p "Press Enter to exit..."
    exit 1
fi

# Check for input.csv
if [ ! -f "input.csv" ]; then
    echo "ERROR: input.csv not found"
    echo "Please create input.csv with the required columns:"
    echo "- URL Slug"
    echo "- Meta Title"
    echo "- Description"
    read -p "Press Enter to exit..."
    exit 1
fi

# Create output directories if they don't exist
mkdir -p generated_images
mkdir -p logs

# Run the application
echo "Starting application..."
python main.py input.csv

# If there's an error, wait before closing
if [ $? -ne 0 ]; then
    echo "Application exited with an error"
    read -p "Press Enter to exit..."
fi
