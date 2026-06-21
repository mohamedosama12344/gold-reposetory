# Cairo Bullion Board — Live Gold & FX Dashboard

A Flask app showing the live gold price per gram (24K/22K/21K/18K) and the
top 5 currencies (USD, EUR, GBP, SAR, AED) against the Egyptian pound,
auto-refreshing in the browser every 30 seconds.

## Data sources (free, no API key)
- Gold: `https://api.gold-api.com/price/XAU` — spot price per troy ounce in USD
- FX: `https://open.er-api.com/v6/latest/USD` — daily rates, USD base

Both are queried server-side and cached for 60 seconds.

## Run locally (no Docker)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
# open http://localhost:5000
```

## Run with Docker directly
```bash
docker build -t gold-dashboard .
docker run -d --name gold-dashboard --restart unless-stopped -p 5000:5000 gold-dashboard
```

## Project layout
```
app.py                  Flask app: caches & serves /api/prices
templates/index.html    The dashboard UI
requirements.txt
Dockerfile               Builds the app into a container image
Jenkinsfile               CI/CD pipeline: build image -> run container -> health check
```

## Keeping it alive through Jenkins (Docker-in-Docker setup)

If Jenkins itself runs as a container (e.g. you start it with
`docker start jenkins`), it has no `sudo` and no `systemd` inside it — so a
systemd-based deploy will always fail with `sudo: command not found`. The
correct pattern here is: Jenkins builds a Docker image and starts a
**sibling container** on the host's Docker daemon, with `--restart unless-stopped`.
That flag is what actually keeps the app alive — through crashes and host
reboots — independent of whether Jenkins or any build is running.

### One-time setup: give the Jenkins container access to Docker
Check first:
```bash
docker exec jenkins which docker
```
If empty, recreate the Jenkins container with the host's Docker socket and
CLI mounted in (this lets Jenkins issue docker commands that run on the
host's Docker daemon — "Docker outside of Docker"):
```bash
docker stop jenkins
docker rm jenkins
docker run -d --name jenkins \
  -p 8080:8080 -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(which docker):/usr/bin/docker \
  jenkins/jenkins:lts
```
Use whatever volume name your existing Jenkins data lives in, so you don't
lose your jobs/credentials — check with `docker inspect jenkins` first if
you're not sure.

### Jenkins job
Point a Jenkins Pipeline job at this repo; it auto-detects the `Jenkinsfile`.
Each build:
1. checks out the code
2. `docker build`s the image, tagged with the build number and `latest`
3. removes any previous `gold-dashboard` container and starts a new one with
   `--restart unless-stopped`
4. runs a health check **from inside the app container** (not via
   `localhost` on the Jenkins side, since Jenkins is in its own network
   namespace)

Add a GitHub webhook or "Poll SCM" trigger so every push redeploys.

### Manually checking it's alive any time
```bash
docker ps                         # should show gold-dashboard, Up
docker logs -f gold-dashboard
curl http://<host>:5000/healthz
```

## Notes
- `--restart unless-stopped` survives both crashes and `docker` daemon /
  host restarts, but won't restart a container you deliberately stopped —
  use `always` instead if you want it to come back even after a manual stop.
- Swap `SAR`/`AED` in `app.py`'s `TOP_CURRENCIES` list for any other
  currencies you'd rather track.
- Put this behind Nginx with TLS if it's going to be public-facing.
