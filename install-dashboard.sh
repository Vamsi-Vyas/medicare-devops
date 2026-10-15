#!/usr/bin/env bash
set -euo pipefail
ROOT="/home/ec2-user/medicare-dashboard"
sudo mkdir -p "$ROOT"
sudo chown ec2-user:ec2-user "$ROOT"
cp -r dashboard/. "$ROOT/"
python3 -m venv "$ROOT/venv"
"$ROOT/venv/bin/pip" install --upgrade pip
"$ROOT/venv/bin/pip" install -r "$ROOT/requirements.txt"
chmod 700 "$ROOT"
chmod 600 "$ROOT/app.py"
if [ ! -f "$ROOT/.env" ]; then
  PASS="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
  printf 'DASHBOARD_PASSWORD=%s\nKUBECONFIG=/home/ec2-user/.kube/config\n' "$PASS" > "$ROOT/.env"
  chmod 600 "$ROOT/.env"
  echo "Save this dashboard password now: $PASS"
else
  echo "Existing dashboard password retained."
fi
sudo tee /etc/systemd/system/medicare-dashboard.service >/dev/null <<'UNIT'
[Unit]
Description=MediCare DevOps Dashboard
After=network.target docker.service k3s.service jenkins.service
[Service]
Type=simple
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/medicare-dashboard
EnvironmentFile=/home/ec2-user/medicare-dashboard/.env
Environment=KUBECONFIG=/home/ec2-user/.kube/config
ExecStart=/home/ec2-user/medicare-dashboard/venv/bin/python /home/ec2-user/medicare-dashboard/app.py
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=read-only
ReadWritePaths=/home/ec2-user/medicare-dashboard
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now medicare-dashboard
sudo systemctl --no-pager --full status medicare-dashboard || true
echo "Unauthenticated local check; HTTP 401 is expected:"
curl -sS -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:5000/ || true
echo "Do not expose port 5000 in the EC2 security group."
