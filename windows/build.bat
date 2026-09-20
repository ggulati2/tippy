@echo off
rem Builds the standalone Windows app:  windows\build.bat
rem Result: dist\Tippy\Tippy.exe (a folder) and, if Inno Setup is installed, dist\Tippy-Setup-<version>.exe.
rem It must be run on Windows (PyInstaller cannot build for another system). Normally CI does this for you:
rem see .github/workflows/windows-app.yml.
setlocal
cd /d "%~dp0\.."
set /p TIPPY_VERSION=<VERSION

py -3 -m venv .venv-build || goto :fail
call .venv-build\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt -r requirements-build.txt || goto :fail

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
pyinstaller --noconfirm --clean --distpath dist --workpath build packaging\tippy.spec || goto :fail

where iscc >nul 2>nul
if %errorlevel%==0 (
  iscc windows\tippy.iss || goto :fail
) else (
  echo Inno Setup is not installed: skipping the single-file installer. The folder dist\Tippy works on its own.
)
echo Done. See the dist folder.
exit /b 0
:fail
echo The build failed. See the messages above.
exit /b 1
