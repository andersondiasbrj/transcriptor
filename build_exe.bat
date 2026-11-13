@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\activate.bat (
    echo Ambiente virtual nao encontrado. Execute install_windows.bat primeiro.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pyinstaller
pyinstaller --noconfirm --clean --windowed --onedir ^
  --name AudioForensicTranscriber ^
  --icon assets\audio_forensic.ico ^
  --add-data "assets;assets" ^
  --collect-all reportlab ^
  --collect-all PIL ^
  --collect-all matplotlib ^
  --collect-all faster_whisper ^
  desktop_app.py
if errorlevel 1 (
    echo Falha ao compilar o aplicativo.
    pause
    exit /b 1
)
echo.
echo Executavel criado em dist\AudioForensicTranscriber\AudioForensicTranscriber.exe
echo IMPORTANTE: FFmpeg/FFprobe devem estar instalados no Windows e disponiveis no PATH.
echo O primeiro uso do Faster-Whisper pode baixar os modelos de transcricao.
pause
