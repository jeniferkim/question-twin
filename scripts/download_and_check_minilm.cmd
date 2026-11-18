@echo off
setlocal
pushd "%~dp0.."
echo This downloads public CPU packages and the MiniLM model.
echo It uses synthetic questions only and does not upload your consultation data.
echo No Git or GitHub operations are performed.
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install torch --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install sentence-transformers
if errorlevel 1 goto failed
".venv\Scripts\python.exe" scripts\minilm_smoke.py --revision e8f8c211226b894fcb81acc59f3b34ba3efd5f42 --download
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip freeze > scripts\reports\minilm_environment.txt
if errorlevel 1 goto failed
echo Passed. See scripts\reports\minilm_smoke.json and minilm_environment.txt.
popd
pause
exit /b 0
:failed
echo Setup or smoke test failed. Keep this window open for troubleshooting.
popd
pause
exit /b 1
