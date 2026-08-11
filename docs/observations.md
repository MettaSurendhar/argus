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

**Status:** ✅ resolved — native Docker Engine install fixed this.

---

## 2. WSL2 distro terminates silently mid-`docker build` (Step 3/5)

**Environment:** WSL2 (Ubuntu 22.04), project on `/mnt/d/MettaProjects/argus-test`

**Symptom:** `setup.sh` was mid-way through Step 3/5 (building the agent's
Docker image) — `docker build` completed all 9 steps and finished
"exporting to image" — then the terminal jumped straight to a **Windows
PowerShell prompt** (`PS D:\>`) with no error, no Step 4/5 header, no exit
code. The whole WSL2 distro terminated, not just the script.

**Cause:** The project directory is on `/mnt/d/` — a Windows NTFS drive
mounted into WSL2 via the 9p protocol, not WSL2's native Linux filesystem.
File I/O across that boundary is drastically slower than native disk,
which shows up directly in the log timings: `pip install` took **890.9s**
(~15 min) and layer export took **213.8s** — both abnormal. Under that much
sustained I/O pressure plus Docker's memory use during the build, the
WSL2 VM hit a resource ceiling and was killed/reset by Windows.

**Fix:**
1. Move the project onto WSL2's native filesystem instead of `/mnt/d/`:
   ```bash
   mkdir -p ~/projects
   cp -r /mnt/d/MettaProjects/argus-test ~/projects/argus
   cd ~/projects/argus
   ```
2. Give WSL2 more headroom — create `C:\Users\<you>\.wslconfig` (from
   Windows) with:
   ```ini
   [wsl2]
   memory=6GB
   processors=4
   ```
   then `wsl --shutdown` from PowerShell and reopen.
3. Clean up any half-started state before retrying:
   ```bash
   docker ps -a
   minikube status   # minikube delete if it's left over from the crashed run
   ```

**Status:** ⏳ pending confirmation — re-run `./setup.sh` from the native
filesystem path and update this entry with the result.

---

## 3. Step 4/5 fails: `docker: --env-file: open .env: no such file or directory`

**Environment:** WSL2, project moved to `~/projects/argus` (native
filesystem, per issue #2's fix)

**Cause:** No `.env` file in the project root. `docker build` (Step 3)
doesn't read `.env` at all, so a missing `.env` doesn't surface until
Step 4, the first step that actually runs `docker run --env-file .env
...`. In this case the project directory had been freshly copied
(`cp -r ... ~/projects/argus`) without `.env` ever having been created
in it — an easy step to skip when moving/re-cloning the project.

**Fix:**
```bash
cp .env.example .env
# fill in GROQ_API_KEY (or OPENROUTER_API_KEY) in .env
./setup.sh
```
Re-running is cheap once minikube/SigNoz/the Docker image are already up —
`setup.sh` skips straight to Step 4.

**Status:** ⏳ pending confirmation.

---

## 4. HF Hub unauthenticated rate-limit warning at Step 4/5

**Symptom:**
```
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
```

**Cause:** `sentence-transformers` downloads the embedding model from
Hugging Face Hub anonymously by default. Not fatal on its own, but slower
and can hit rate limits.

**Fix:** Added `HF_TOKEN=` to `.env.example` (get a free token at
https://huggingface.co/settings/tokens, read access is enough). Docker
passes `.env` straight into the container's environment, and
`huggingface_hub` picks up `HF_TOKEN` automatically — no code changes
needed.

**Status:** ✅ resolved.
