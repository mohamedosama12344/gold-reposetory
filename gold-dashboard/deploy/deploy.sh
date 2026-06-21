#!/usr/bin/env bash
# Deploys the gold dashboard and (re)starts it as a systemd service so it
# keeps running even after the Jenkins job finishes.
#
# Expected to run on the target server, e.g. as a Jenkins SSH/pipeline step:
#   ./deploy/deploy.sh
#
# First-time setup (run once, as root):
#   sudo useradd -r -s /usr/sbin/nologin deploy   # if the user doesn't exist
#   sudo mkdir -p /opt/gold-dashboard
#   sudo chown deploy:deploy /opt/gold-dashboard
#   sudo cp deploy/gold-dashboard.service /etc/systemd/system/
#   sudo systemctl daemon-reload
#   sudo systemctl enable gold-dashboard

set -euo pipefail

APP_DIR="/opt/gold-dashboard"
SERVICE_NAME="gold-dashboard"

echo ">> Syncing application files to $APP_DIR"
sudo rsync -a --delete \
  --exclude 'venv' \
  --exclude '.git' \
  ./ "$APP_DIR/"

echo ">> Ensuring virtualenv + dependencies"
sudo -u deploy bash -c "
  cd $APP_DIR
  python3 -m venv venv --upgrade-deps 2>/dev/null || python3 -m venv venv
  ./venv/bin/pip install --quiet -r requirements.txt
"

echo ">> Restarting service"
sudo systemctl restart "$SERVICE_NAME"

echo ">> Waiting for health check"
for i in {1..10}; do
  if curl -sf http://localhost:5000/healthz > /dev/null; then
    echo "Service is up."
    exit 0
  fi
  sleep 1
done

echo "Health check failed after restart" >&2
sudo systemctl status "$SERVICE_NAME" --no-pager || true
exit 1
