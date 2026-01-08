@echo off
setlocal

echo Step 2 starting
for /l %%i in (1,1,2) do (
  timeout /t 1 /nobreak >nul
  echo Step 2 progress %%i0%%
)

echo Step 2 failed
exit /b 2
