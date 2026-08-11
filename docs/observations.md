# Setup observations

Running log of issues hit while testing `setup.sh` on a real machine, and how
they were resolved. Not part of the polished README — this is a working
troubleshooting log kept during initial rollout.

Each entry: what failed, what the actual cause was, how it was fixed.

---

## 1. minikube exits with `PROVIDER_DOCKER_VERSION_EXIT_1`

**Environment:** WSL2 (Ubuntu 22.04), project on `/mnt/d/...` (Windows drive
mounted into WSL)

**Error:**
```
Exiting due to PROVIDER_DOCKER_VERSION_EXIT_1: "docker version --format <no value>-<no value>:<no value>" exit status 1
```

**Cause:** Initial hypothesis (daemon not started / user not in `docker`
group) was wrong. `groups $USER` already showed `docker`, and
`systemctl status docker` returned `Unit docker.service could not be
found` — meaning Docker Engine was **never installed** in this WSL distro
at all. `docker version` / `docker ps` returning *"The command 'docker'
could not be found... activate the WSL integration in Docker Desktop
settings"* confirms it: what's present is only Docker Desktop's WSL
integration stub, not a native Docker install. This is exactly the
Docker Desktop path the README already steers away from (ClickHouse
Keeper crash bug on Windows) — the fix is a native Docker Engine install
inside WSL2, not enabling Docker Desktop integration.

**Fix:** Install Docker Engine natively via apt (official Docker repo, not
the Desktop app):
```bash
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do
  sudo apt-get remove -y $pkg
done
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
docker run hello-world
```
If Docker Desktop is also installed on the Windows side, turn off its WSL
integration for this distro (Settings → Resources → WSL Integration) so it
doesn't conflict with the native install.

**Status:** ⏳ pending confirmation — re-run `./setup.sh` after install and
update this entry with the result.
