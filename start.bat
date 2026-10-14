@echo off
chcp 65001 >nul
title Depotwerkstatt - Werkbank 02: Zitat-Pruefer
cd /d "%~dp0"

echo.
echo === Werkbank 02: Zitat-Pruefer, ohne KI ===
echo.

where py >nul 2>&1
if errorlevel 1 (
    echo Python wurde nicht gefunden.
    echo Bitte zuerst installieren: https://www.python.org/downloads/windows/
    echo Beim Installieren den Haken "Add python.exe to PATH" setzen, dann diese Datei erneut starten.
    echo.
    pause
    exit /b 1
)

echo Pruefe Abhaengigkeit "pypdf" ...
py -m pip install --quiet --disable-pip-version-check pypdf
if errorlevel 1 (
    echo Installation von "pypdf" fehlgeschlagen. Internetverbindung pruefen.
    pause
    exit /b 1
)

echo.
echo Schritt 1: Offline-Test mit fiktiven Daten ...
py werkbank02.py --demo
echo.

echo Schritt 2: Tipp - Dateien einfach mit der Maus in dieses Fenster ziehen, dann Enter.
set /p ANTWORT=KI-Antwort (.txt) oder Enter zum Beenden: 
if "%ANTWORT%"=="" goto ende
set /p DOK1=Erstes Dokument (.pdf): 
set /p DOK2=Zweites Dokument (.pdf) oder Enter, falls keins: 

echo.
if "%DOK2%"=="" (
    py werkbank02.py %ANTWORT% %DOK1%
) else (
    py werkbank02.py %ANTWORT% %DOK1% %DOK2%
)
echo.
echo Das Protokoll liegt im Ordner "output". Die .md-Datei in Cursor oder einem Editor oeffnen.

:ende
echo.
pause
