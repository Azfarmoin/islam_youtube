"""Push dashboard settings to config.yaml in your GitHub repo (so GitHub Actions runs use them).
Only whitelisted setting paths are touched, comments and layout are kept, and the token is never printed or logged.
Token: IVS_GITHUB_TOKEN / GITHUB_TOKEN (environment or .env), else `gh auth token` if the GitHub CLI is logged in.
It needs permission to write repo contents (fine-grained token: Contents = Read and write, for this one repo)."""
from __future__ import annotations
import base64, difflib, os, re, shutil, subprocess
from pathlib import Path
import requests

API = "https://api.github.com"
FILE = "config.yaml"

def _dotenv(root: Path) -> dict:
    out = {}
    try:
        for line in (root / ".env").read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, _, v = line.partition("="); out[k.strip()] = v.strip().strip('"').strip("'")
    except Exception: pass
    return out

def token(root: Path) -> str | None:
    env = _dotenv(root)
    for k in ("IVS_GITHUB_TOKEN", "GITHUB_TOKEN"):
        t = os.environ.get(k) or env.get(k)
        if t: return t
    if shutil.which("gh"):
        try:
            r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=15)
            if r.returncode == 0 and r.stdout.strip(): return r.stdout.strip()
        except Exception: pass
    return None

def repo_slug(root: Path) -> str | None:
    env = _dotenv(root); s = os.environ.get("IVS_GITHUB_REPO") or env.get("IVS_GITHUB_REPO")
    if s and re.fullmatch(r"[\w.-]+/[\w.-]+", s): return s
    try:
        u = subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"], capture_output=True, text=True, timeout=10).stdout.strip()
        m = re.search(r"github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?$", u)
        return m.group(1) if m else None
    except Exception: return None

def _val(v) -> str:
    if isinstance(v, bool): return "true" if v else "false"
    return str(v)

def patch_yaml_text(text: str, path: tuple, value) -> tuple[str, bool]:
    """Change one scalar in YAML text in place, keeping comments. Handles block keys and keys inside a one-line {flow: mapping}."""
    lines = text.split("\n"); lo, indent = 0, -1; idx = None
    for depth, key in enumerate(path):
        found = None
        for i in range(lo, len(lines)):
            ln = lines[i]
            if not ln.strip() or ln.lstrip().startswith("#"): continue
            ind = len(ln) - len(ln.lstrip())
            if ind <= indent: break                       # left the parent block
            if depth == 0 and ind != 0: continue
            if re.match(rf"\s*{re.escape(key)}\s*:", ln) and (depth == 0 or ind > indent):
                found = i; break
        if found is None:
            if depth == len(path) - 1 and idx is not None and "{" in lines[idx]:        # last key lives in the parent's flow mapping
                new, n = re.subn(rf"({re.escape(key)}\s*:\s*)[^,}}#]+?(\s*[,}}])", lambda m: m.group(1) + _val(value) + m.group(2), lines[idx], count=1)
                if n: lines[idx] = new; return "\n".join(lines), True
            return text, False
        idx = found; indent = len(lines[found]) - len(lines[found].lstrip()); lo = found + 1
        if depth < len(path) - 1:
            m = re.match(rf"\s*{re.escape(key)}\s*:\s*\{{", lines[found])                # parent itself is a flow mapping on this line
            if m and depth == len(path) - 2:
                key2 = path[-1]
                new, n = re.subn(rf"({re.escape(key2)}\s*:\s*)[^,}}#]+?(\s*[,}}])", lambda mm: mm.group(1) + _val(value) + mm.group(2), lines[found], count=1)
                if n: lines[found] = new; return "\n".join(lines), True
                return text, False
    ln = lines[idx]
    m = re.match(r"^(\s*" + re.escape(path[-1]) + r"\s*:\s*)([^#\n]*?)(\s*)(#.*)?$", ln)
    if not m: return text, False
    gap = m.group(3) or ""
    if m.group(4):          # keep the comment in the same column where possible
        gap = " " * max(1, len(gap) - (len(_val(value)) - len(m.group(2).strip())))
    lines[idx] = m.group(1) + _val(value) + gap + (m.group(4) or "")
    return "\n".join(lines), True

def apply(text: str, changes: dict[tuple, object]) -> tuple[str, list[str]]:
    skipped = []
    for p, v in changes.items():
        text, ok = patch_yaml_text(text, p, v)
        if not ok: skipped.append(".".join(p))
    return text, skipped

def _hdr(tok): return {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}

def fetch_remote(slug: str, tok: str, http=requests) -> tuple[str, str]:
    r = http.get(f"{API}/repos/{slug}/contents/{FILE}", headers=_hdr(tok), timeout=30)
    if r.status_code == 404: raise RuntimeError(f"{FILE} not found in {slug} (is the project pushed to that repo?)")
    if r.status_code in (401, 403): raise RuntimeError("GitHub refused the token (needs Contents: Read and write on this repository)")
    r.raise_for_status(); j = r.json()
    return base64.b64decode(j["content"]).decode("utf-8"), j["sha"]

def preview(slug: str, tok: str, changes: dict, http=requests) -> dict:
    text, sha = fetch_remote(slug, tok, http); new, skipped = apply(text, changes)
    diff = "".join(difflib.unified_diff(text.splitlines(True), new.splitlines(True), "config.yaml (GitHub now)", "config.yaml (after)", n=0))
    return {"changed": new != text, "diff": diff, "skipped": skipped, "sha": sha}

def push(slug: str, tok: str, changes: dict, message: str = "Update video settings from the dashboard", http=requests) -> dict:
    text, sha = fetch_remote(slug, tok, http); new, skipped = apply(text, changes)
    if new == text: return {"pushed": False, "skipped": skipped, "reason": "GitHub already has these settings"}
    r = http.put(f"{API}/repos/{slug}/contents/{FILE}", headers=_hdr(tok), timeout=30,
                 json={"message": message, "content": base64.b64encode(new.encode("utf-8")).decode(), "sha": sha})
    if r.status_code == 409: raise RuntimeError("config.yaml changed on GitHub while saving; open the page again and retry")
    if r.status_code in (401, 403, 404): raise RuntimeError("GitHub refused the write (token needs Contents: Read and write)")
    r.raise_for_status()
    return {"pushed": True, "skipped": skipped, "commit": (r.json().get("commit") or {}).get("html_url")}

# ---- more GitHub helpers used by the dashboard (same token, same safety rules) ----
def default_branch(slug: str, tok: str, http=requests) -> str:
    r = http.get(f"{API}/repos/{slug}", headers=_hdr(tok), timeout=30)
    if r.status_code in (401, 403, 404): raise RuntimeError("GitHub refused the token for this repository")
    r.raise_for_status(); return r.json().get("default_branch") or "main"

def dispatch(slug: str, tok: str, workflow: str = "daily.yml", inputs: dict | None = None, http=requests) -> None:
    if not re.fullmatch(r"[\w.-]+\.ya?ml", workflow): raise ValueError("bad workflow name")
    body = {"ref": default_branch(slug, tok, http)}
    if inputs: body["inputs"] = inputs
    r = http.post(f"{API}/repos/{slug}/actions/workflows/{workflow}/dispatches", headers=_hdr(tok), json=body, timeout=30)
    if r.status_code in (401, 403): raise RuntimeError("GitHub refused: the token needs Actions: Read and write")
    if r.status_code == 404: raise RuntimeError(f"workflow {workflow} not found in {slug}")
    if r.status_code == 422: raise RuntimeError("GitHub rejected the request (the workflow may not accept that input)")
    r.raise_for_status()

def runs(slug: str, tok: str, n: int = 6, http=requests) -> list[dict]:
    r = http.get(f"{API}/repos/{slug}/actions/runs", params={"per_page": n}, headers=_hdr(tok), timeout=30)
    if r.status_code in (401, 403): raise RuntimeError("GitHub refused: the token needs Actions: Read")
    r.raise_for_status()
    return [{"name": x.get("name"), "status": x.get("status"), "conclusion": x.get("conclusion"), "url": x.get("html_url"), "created": x.get("created_at"), "event": x.get("event")} for x in r.json().get("workflow_runs", [])]

def put_file(slug: str, tok: str, path: str, text: str, message: str, http=requests) -> dict:
    """Create or update one text file in the repo (default branch)."""
    if ".." in path or path.startswith("/"): raise ValueError("bad path")
    url = f"{API}/repos/{slug}/contents/{path}"
    g = http.get(url, headers=_hdr(tok), timeout=30); sha = None
    if g.status_code == 200: sha = g.json().get("sha")
    elif g.status_code in (401, 403): raise RuntimeError("GitHub refused the token (Contents: Read and write)")
    body = {"message": message, "content": base64.b64encode(text.encode("utf-8")).decode()}
    if sha: body["sha"] = sha
    r = http.put(url, headers=_hdr(tok), json=body, timeout=30)
    if r.status_code == 409: raise RuntimeError("the file changed on GitHub while saving; retry")
    if r.status_code in (401, 403, 404): raise RuntimeError("GitHub refused the write (Contents: Read and write)")
    r.raise_for_status()
    return {"commit": (r.json().get("commit") or {}).get("html_url"), "updated": bool(sha)}

# ---- local .env helpers (secrets are written, never read back to the page) ----
def env_set(root: Path, key: str, value: str) -> None:
    if not re.fullmatch(r"[A-Z][A-Z0-9_]{2,60}", key): raise ValueError("bad variable name")
    if not value or "\n" in value or "\r" in value or len(value) > 800: raise ValueError("bad value")
    f = root / ".env"; lines = f.read_text(encoding="utf-8").splitlines() if f.exists() else []
    out, done = [], False
    for ln in lines:
        if re.match(rf"\s*{re.escape(key)}\s*=", ln):
            if not done: out.append(f"{key}={value}"); done = True
        else: out.append(ln)
    if not done: out.append(f"{key}={value}")
    f.write_text("\n".join(out) + "\n", encoding="utf-8")
    try: os.chmod(f, 0o600)
    except Exception: pass

def env_has(root: Path, key: str) -> bool:
    return bool(os.environ.get(key) or _dotenv(root).get(key))

def gh_secret(slug: str, name: str, value: str) -> bool:
    """Upload a repo secret through the GitHub CLI; the value goes on stdin only."""
    if not shutil.which("gh") or not re.fullmatch(r"[A-Z][A-Z0-9_]{2,60}", name): return False
    r = subprocess.run(["gh", "secret", "set", name, "--repo", slug], input=value, text=True, capture_output=True, timeout=60)
    return r.returncode == 0
