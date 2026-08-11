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

**Screenshot:**

![screenshots/observation-1.png](screenshots/observation-1.png)

**Cause:** Initial hypothesis (daemon not started / user not in `docker`
group) was wrong. `groups $USER` already showed `docker`, and
`systemctl status docker` returned `Unit docker.service could not be
found` — meaning Docker Engine was **never installed** in this WSL distro
at all. `docker version` / `docker ps` returning _"The command 'docker'
could not be found... activate the WSL integration in Docker Desktop
settings"_ confirms it: what's present is only Docker Desktop's WSL
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

**Screenshot:**

![screenshots/observation-2.png](screenshots/observation-2.png)

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

**Screenshot:**

![screenshots/observation-3.png](screenshots/observation-3.png)

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

**Screenshot:**

![screenshots/observation-4.png](screenshots/observation-4.png)

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

---

## 5. Step 5/5 fails: MCP server can't read minikube certs inside container

**Symptom:**

```
Error: unable to create kubernetes target provider: failed to create kubernetes rest config from kubeconfig: invalid configuration: [unable to read client-cert /home/metta-unix/.minikube/profiles/minikube/client.crt for minikube due to open /home/metta-unix/.minikube/profiles/minikube/client.crt: no such file or directory, ...]
```

followed by an `mcp.shared.exceptions.MCPError: Connection closed`.

**Cause:** A real bug in `setup.sh`'s `run_agent()`, not a host/environment
issue. It mounted:

```bash
-v "$HOME/.kube:/root/.kube:ro" \
-v "$HOME/.minikube:/root/.minikube:ro" \
```

But minikube's generated kubeconfig references cert files by **absolute
host path** (`/home/<user>/.minikube/profiles/minikube/client.crt`), not
by a path relative to `$HOME`. Mounting `$HOME/.minikube` to
`/root/.minikube` creates that path inside the container, but the
kubeconfig still points at `/home/<user>/.minikube/...`, which was never
mounted anywhere — the file reference and the actual mount point don't
match, so every cert read fails.

**Fix:** Stopped relying on matching host/container paths at all. Instead,
flatten the kubeconfig — `kubectl config view --minify --flatten` embeds
all cert data directly into the kubeconfig as base64, so there's no
external file path to get wrong:

```bash
kubectl config view --minify --flatten > /tmp/argus-kubeconfig
docker run ... -v "/tmp/argus-kubeconfig:/root/.kube/config:ro" ...
```

No longer needs `.minikube` mounted at all. This is portable across any
host username/home-directory layout, not just the machine it happened to
be developed on.

**Status:** ⏳ pending confirmation — re-run `./setup.sh` and update this
entry with the result.

---

## 6. Traces not visible in SigNoz UI on the very first run (benign)

**Symptom:** After the first-ever successful `./setup.sh` run against a
freshly deployed SigNoz instance, no traces/services showed up in the UI
on first login. Re-running the scenarios a second time, traces appeared
normally.

**Investigated:** Checked whether `BatchSpanProcessor` spans were being
dropped on process exit (the classic cause) — they aren't:
`instrumentation/main.py` calls `flush()` →
`provider.force_flush()` in a `finally` block after every `diagnose()`
call, so spans are always pushed out before the CLI process exits. Code
is correct.

**Likely cause:** Cold-start propagation delay on a freshly created
ClickHouse schema (`foundryctl cast` had just deployed SigNoz moments
before). Newly-seen-service detection in the UI appears to lag slightly
behind the first-ever write on a brand new stack; by the second run the
pipeline had already warmed up and new spans appeared immediately.

**Status:** ✅ not a bug — benign one-time cold start, no fix needed.
Note it if it happens again on a fresh deploy: just wait ~30s–1min and
refresh, or run a scenario a second time.

**Follow-up fix (proactive, not confirmed to have been strictly
necessary for what was observed above, but closes a real race):**
`signoz_fully_ready()` only checked the UI/query-service and ClickHouse
Keeper — not the OTLP collector on port 4317, which is what spans are
actually sent to. On the run above, ~20+ minutes elapsed between SigNoz
coming up and Step 5 starting (slow first-time `docker build` + `pip
install`), which incidentally gave the collector plenty of time to warm
up. On a **cached re-run** (image + RAG index already built), that
elapsed-time cushion disappears — Step 5 could start seconds after
SigNoz deploys, hitting the same race far more easily. Added an explicit
wait for the OTLP port right before Step 5 starts, instead of relying on
however long steps 2-4 happen to take:

```bash
otlp_collector_ready() {
    (exec 3<>/dev/tcp/localhost/4317) 2>/dev/null
}
# polled in a loop immediately before the first scenario runs
```

Also switched `signoz_fully_ready()`'s UI check from curling the root
page to SigNoz's documented `/api/v1/health` endpoint, a more precise
readiness signal.
