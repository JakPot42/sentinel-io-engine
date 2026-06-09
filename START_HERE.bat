@echo off
echo.
echo  SENTINEL -- Influence Operations Detection Engine
echo  ================================================
echo.

if not exist venv (
    echo [1/3] Creating virtual environment...
    python -m venv venv
)

echo [2/3] Installing dependencies...
venv\Scripts\pip install -r requirements.txt --quiet

if not exist .env (
    echo [!] .env file not found. Creating from .env.example...
    copy .env.example .env
    echo [!] Edit .env and add your ANTHROPIC_API_KEY before using AI features.
)

echo [3/3] Starting server on http://localhost:8000
echo.
echo  DEMO: visit http://localhost:8000/seed to load Operation STEEL ECHO
echo.
venv\Scripts\uvicorn main:app --reload --host 127.0.0.1 --port 8000
