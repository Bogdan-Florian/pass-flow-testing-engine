# Remote environment setup for PASS batches (hardcoded creds)
# Run from PowerShell: powershell -NoProfile -ExecutionPolicy Bypass -File setup_remote_env.ps1

$HostName = "157.180.46.211"
$User     = "root"
$Password = "ArbqsLJEmwFvkNb9dFcM1"  # not injected; scp/ssh will prompt if needed

# Bash script that will run on the remote host
$RemoteScript = @'
#!/usr/bin/env bash
set -euo pipefail

BASE=/opt/pass_prod
PRODUCTS=(
  "life:new_business,revocation,termination"
  "auto:new_business,revocation"
  "health:new_business"
)

echo "Creating base at $BASE"
mkdir -p "$BASE"

for entry in "${PRODUCTS[@]}"; do
  IFS=':' read -r product ops <<<"$entry"
  product_dir="$BASE/$product"
  mkdir -p "$product_dir"
  IFS=',' read -ra op_list <<<"$ops"
  for op in "${op_list[@]}"; do
    op_dir="$product_dir/$op"
    mkdir -p "$op_dir/input"
    script="$op_dir/run.sh"

    cat > "$script" <<'EOB'
#!/usr/bin/env bash
set -e
this_dir=$(cd "$(dirname "$0")"; pwd)
input_dir="$this_dir/input"
echo "Running $(basename "$0")"
echo "Input folder: $input_dir"
ls -la "$input_dir" || true
sleep 1
echo "Done"
EOB

    chmod +x "$script"
  done
done

echo "Layout created under $BASE"
if command -v tree >/dev/null 2>&1; then
  tree "$BASE"
else
  find "$BASE" -maxdepth 4 -type f
fi
'@

$tmp = New-TemporaryFile
Set-Content -Path $tmp -Value $RemoteScript -NoNewline -Encoding UTF8

scp $tmp "$User@$HostName:/tmp/setup_pass_env.sh"
ssh "$User@$HostName" "chmod +x /tmp/setup_pass_env.sh && sudo /tmp/setup_pass_env.sh"

Remove-Item $tmp -Force
