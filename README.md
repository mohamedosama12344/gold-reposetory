# Cairo Bullion Board — Live Gold & FX Dashboard

A Flask app showing the live gold price per gram (24K/22K/21K/18K) and the
top 5 currencies (USD, EUR, GBP, SAR, AED) against the Egyptian pound,
auto-refreshing in the browser every 30 seconds.

## Data sources (free, no API key)
- Gold: `https://api.gold-api.com/price/XAU` — spot price per troy ounce in USD
- FX: `https://open.er-api.com/v6/latest/USD` — daily rates, USD base

Both are queried server-side and cached for 60 seconds, so the page can be
hit by many visitors without hammering the upstream APIs. If a fetch ever
fails, the app keeps serving the last good values and flags it in the status
bar instead of crashing.

## Run locally
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
# open http://localhost:5000
```

## Project layout
```
app.py                       Flask app: caches & serves /api/prices
templates/index.html         The dashboard UI
requirements.txt
Jenkinsfile                  CI/CD pipeline: install -> deploy -> health check
deploy/deploy.sh             Syncs code to /opt/gold-dashboard, restarts service
deploy/gold-dashboard.service  systemd unit (gunicorn, Restart=always)
```

## Keeping it alive through Jenkins

Jenkins jobs are not meant to run a server in the foreground — the process
dies with the build. So the app is deployed as a **systemd service**, and
Jenkins' only job is to update the code and restart that service. systemd
(`Restart=always`) is what actually keeps it alive 24/7, survives reboots,
and restarts it if it ever crashes.

### One-time server setup
```bash
sudo useradd -r -s /usr/sbin/nologin deploy
sudo mkdir -p /opt/gold-dashboard
sudo chown deploy:deploy /opt/gold-dashboard
sudo cp deploy/gold-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gold-dashboard
```

Give the Jenkins user passwordless sudo for just the commands it needs, e.g.
in `/etc/sudoers.d/jenkins-deploy`:
```
jenkins ALL=(ALL) NOPASSWD: /usr/bin/rsync, /bin/systemctl restart gold-dashboard, /bin/systemctl status gold-dashboard
```

### Jenkins job
Point a Jenkins Pipeline job at this repo (it will auto-detect the
`Jenkinsfile`). Each build:
1. checks out the code
2. installs dependencies into a throwaway venv and sanity-checks the import
3. runs `deploy/deploy.sh`, which syncs files to `/opt/gold-dashboard`,
   installs deps into the **persistent** venv there, and restarts the
   `gold-dashboard` systemd service
4. curls `/healthz` to confirm it came back up

Add a "Poll SCM" or webhook trigger so every push redeploys automatically.

### Manually checking it's alive any time
```bash
sudo systemctl status gold-dashboard
curl http://localhost:5000/healthz
journalctl -u gold-dashboard -f
```

## Notes / things to adjust for your setup
- If Jenkins deploys to a **different machine** than the one it builds on,
  replace the `Deploy` stage with an `sshagent` step that scps the repo and
  runs `deploy.sh` remotely, instead of local `sudo rsync`.
- Swap `SAR`/`AED` in `app.py`'s `TOP_CURRENCIES` list for any other
  currencies you'd rather track.
- Put this behind Nginx with TLS if it's going to be public-facing; Gunicorn
  is fine for local network use as-is.
