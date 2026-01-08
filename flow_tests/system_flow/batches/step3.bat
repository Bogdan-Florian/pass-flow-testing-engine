@echo off
setlocal

echo Step 3 starting
for /l %%i in (1,1,5) do (
  timeout /t 1 /nobreak >nul
  echo Step 3 progress %%i0%%
)

echo Step 3 complete
exit /b 0
