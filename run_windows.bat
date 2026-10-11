@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Virtual environment not found. Create it with: python -m venv .venv
  echo Then run: .venv\Scripts\python -m pip install -r requirements.txt
  pause
  exit /b 1
)
.venv\Scripts\python -m streamlit run app.py
