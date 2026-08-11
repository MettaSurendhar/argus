# Setup guide

Full walkthrough from a bare machine to a running Argus + SigNoz stack.
Already have some tools? Skip to whichever step you need. Quick summary
instead: see the [README](../README.md#prerequisites).

- [0. Windows only — WSL2](#0-windows-only--wsl2)
- [1. Docker Engine](#1-docker-engine)
- [2. minikube + kubectl](#2-minikube--kubectl)
- [3. foundryctl](#3-foundryctl)
- [4. Get the repo running](#4-get-the-repo-running)
- [5. Screenshots](#5-screenshots-of-setupsh-execution)
- [Stopping and cleaning up](#stopping-and-cleaning-up)
- [Troubleshooting](#troubleshooting)

---

## 0. Windows only — WSL2

SigNoz's ClickHouse Keeper segfaults under Docker Desktop's virtualization
layer on Windows. Needs **native Docker Engine inside WSL2**, not Docker
Desktop. macOS/Linux: skip to step 1.

1. Install WSL2 with Ubuntu: [Microsoft's guide](https://learn.microsoft.com/windows/wsl/install)
2. Confirm systemd is enabled:
```bash
   cat /etc/wsl.conf
```
   Should contain:
```ini
   [boot]
   systemd=true
```
   Missing it? Add it, run `wsl --shutdown` from PowerShell, reopen WSL.
3. Run **every command below inside WSL2 Ubuntu**, not PowerShell.
4. **Use WSL2's native filesystem, not `/mnt/c/...` or `/mnt/d/...`.**
   - Windows drives mounted into WSL2 are much slower for file I/O
   - Bad enough that a `docker build` under that load can crash the whole
     WSL2 VM mid-build (see [`docs/faq.md`](faq.md))
   - Clone under your Linux home instead:
```bash
     mkdir -p ~/projects
     git clone <your-repo-url> ~/projects/argus
     cd ~/projects/argus
```
   - `setup.sh` checks for this and warns if detected

See also: [Installing SigNoz on Windows: the Fastest Way](https://medium.com/@mettasurendhar/installing-signoz-on-windows-the-fastest-way-5-minutes-no-docker-desktop-eb7c581ff246)

## 1. Docker Engine

### Already have Docker?

```bash
docker version
systemctl status docker
```

- **Both succeed** → done, skip to step 2
- **`docker` not found, but Docker Desktop is on Windows** → you only
  have the WSL integration stub. Do "Fresh install" below, don't enable
  Desktop's WSL integration — that's exactly the ClickHouse Keeper bug
- **`docker.io` or snap version installed** → conflicts with the apt
  package, remove first:
```bash
  sudo apt-get remove -y docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc
  sudo snap remove docker 2>/dev/null || true
```
  then continue below
- **Docker Desktop's WSL integration is on** → turn it off (Settings →
  Resources → WSL Integration) so it doesn't fight the native install

### Fresh install (native Docker Engine via apt)

```bash
# Remove conflicting/unofficial packages (safe if none installed)
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do
  sudo apt-get remove -y $pkg
done

# Add Docker's GPG key + apt repo
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine + plugins
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start it, enable on boot
sudo systemctl enable --now docker

# Run docker without sudo
sudo usermod -aG docker $USER
```

**Important:** after `usermod`, fully close and reopen your terminal
(WSL: `wsl --shutdown` from PowerShell, reopen) — group membership
doesn't apply to an already-open shell.

### Verify

```bash
docker run hello-world
```
Prints "Hello from Docker!" → ready for step 2.

## 2. minikube + kubectl

```bash
# minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
rm minikube-linux-amd64
minikube version

# kubectl (skip if already installed)
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
rm kubectl
kubectl version --client
```

Full docs / other platforms: https://minikube.sigs.k8s.io/docs/start/

- No need to `minikube start` manually — `setup.sh` starts/reuses the
  cluster itself
- Want to sanity-check in isolation first? `minikube start --driver=docker`,
  then `minikube delete` so `setup.sh` starts clean

## 3. foundryctl

Deploys SigNoz.

```bash
curl -fsSL https://signoz.io/foundry.sh | bash
```

Full docs / manual install (air-gapped environments):
https://github.com/SigNoz/foundry/blob/main/docs/getting-started.md

## 4. Get the repo running

```bash
git clone <your-repo-url> argus
cd argus
cp .env.example .env   # fill in your GROQ_API_KEY (or OPENROUTER_API_KEY)
chmod +x setup.sh
./setup.sh
```

**Windows/WSL2:** run from inside WSL2 Ubuntu, under your Linux home
(e.g. `~/projects/argus`) — not `/mnt/c/` or `/mnt/d/`. See step 0.

`setup.sh`:
- Starts/reuses a minikube cluster
- Deploys SigNoz via Foundry
- Builds the agent's Docker image + RAG index
- Injects each of the 3 demo scenarios and runs the agent against them,
  printing progress at every step
- Runs minikube and Foundry directly on the host, not through a
  container's mounted docker socket (see the script's header comment
  for why)

Want to run things by hand instead (re-run a single scenario, work
outside Docker, poke at an intermediate step)? See the README's
["Running things by hand"](../README.md#running-things-by-hand).

## 5. Screenshots of setup.sh execution

![screenshots/setup-1.png](screenshots/setup-1.png)
![screenshots/setup-2.png](screenshots/setup-2.png)
![screenshots/setup-3.png](screenshots/setup-3.png)
![screenshots/setup-4.png](screenshots/setup-4.png)
![screenshots/setup-5.png](screenshots/setup-5.png)
![screenshots/setup-6.png](screenshots/setup-6.png)
![screenshots/setup-7.png](screenshots/setup-7.png)
![screenshots/setup-8.png](screenshots/setup-8.png)

## Stopping and cleaning up

### Quick check — what's running

```bash
minikube status
docker ps
```

### Pause (keeps all data, fast to resume)

```bash
minikube stop
docker stop $(docker ps -q --filter "name=signoz-")
```

### Full teardown (frees all resources, next run starts clean)

```bash
# 1. Delete the minikube cluster entirely
minikube delete

# 2. Tear down the SigNoz stack (foundryctl has no "down" command — only
#    gauge/forge/cast/gen — so use the compose file it generated)
docker compose -f pours/deployment/compose.yaml down
# add -v to also delete SigNoz's stored data (traces, dashboards, alerts):
# docker compose -f pours/deployment/compose.yaml down -v
```

### Confirm it's stopped

```bash
docker ps -a       # should show no signoz-* or minikube containers running
minikube status     # should report "Profile ... not found" or similar
```

## Troubleshooting

- Quick fixes for likely errors: [`docs/faq.md`](faq.md) — check here first
- Full diagnosis detail (if the quick fix doesn't match your case):
  [`docs/observations.md`](observations.md)
- Hit something new? That's the place to add it
