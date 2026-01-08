@echo off
setlocal

echo Step 1 starting
for /l %%i in (1,1,3) do (
  timeout /t 1 /nobreak >nul
  echo Step 1 progress %%i0%%
)

echo Step 1 complete
exit /b 0
