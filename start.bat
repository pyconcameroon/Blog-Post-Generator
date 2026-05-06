@echo off
echo Starting Blog Post Generator in development mode...

:: Check if virtual environment exists
if not exist "ENVIRONMENT\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv ENVIRONMENT
)

:: Activate virtual environment
call ENVIRONMENT\Scripts\activate.bat

:: Install/upgrade dependencies
echo Installing dependencies...
pip install -r requirements.txt

:: Download NLTK data if not already downloaded
echo Checking NLTK data...
python -m nltk.downloader punkt averaged_perceptron_tagger maxent_ne_chunker words stopwords

:: Check for .env file
if not exist ".env" (
    echo WARNING: .env file not found
    echo Copying .env.example to .env...
    copy .env.example .env
    echo Please edit .env with your credentials before continuing
    pause
    exit /b
)

:: Check for input.csv
if not exist "input.csv" (
    echo ERROR: input.csv not found
    echo Please create input.csv with the required columns:
    echo - URL Slug
    echo - Meta Title
    echo - Description
    pause
    exit /b
)

:: Create output directories if they don't exist
if not exist "generated_images" mkdir generated_images
if not exist "logs" mkdir logs

:: Run the application
echo Starting application...
python main.py input.csv

:: Keep window open if there's an error
if errorlevel 1 (
    echo Application exited with an error
    pause
)
