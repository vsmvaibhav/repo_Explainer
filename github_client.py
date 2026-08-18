"""
github_client.py
-----------------
Talks to the public GitHub REST API to pull the minimum data needed to
explain a repository: metadata, the file tree, and the contents of a
handful of "key" files. No authentication is required for public repos,
but unauthenticated requests are rate-limited (60/hour per IP), so keep
calls to a minimum.
"""

import os
import re
import requests

GITHUB_API = "https://api.github.com"
RAW_BASE = "https://raw.githubusercontent.com"


def _auth_headers() -> dict:
    """Attach a GitHub token if one is set, to get 5,000 req/hour instead of 60."""
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

# Extension -> human-readable tech stack label
TECH_BY_EXTENSION = {
    ".py": "Python", ".ipynb": "Jupyter Notebook",
    ".js": "JavaScript", ".jsx": "React (JSX)", ".ts": "TypeScript", ".tsx": "React (TSX)",
    ".java": "Java", ".kt": "Kotlin", ".go": "Go", ".rs": "Rust",
    ".rb": "Ruby", ".php": "PHP", ".c": "C", ".cpp": "C++", ".cs": "C#",
    ".swift": "Swift", ".m": "Objective-C", ".scala": "Scala",
    ".html": "HTML", ".css": "CSS", ".scss": "SCSS",
    ".sql": "SQL", ".sh": "Shell", ".yml": "YAML", ".yaml": "YAML",
}

# Filename -> framework/tooling signal
TECH_BY_FILENAME = {
    "requirements.txt": "Python (pip)", "pyproject.toml": "Python (Poetry/PEP 621)",
    "package.json": "Node.js", "yarn.lock": "Yarn", "pnpm-lock.yaml": "pnpm",
    "pom.xml": "Java (Maven)", "build.gradle": "Java/Kotlin (Gradle)",
    "go.mod": "Go modules", "cargo.toml": "Rust (Cargo)",
    "gemfile": "Ruby (Bundler)", "dockerfile": "Docker",
    "docker-compose.yml": "Docker Compose", "next.config.js": "Next.js",
    "vite.config.js": "Vite", "angular.json": "Angular", "vue.config.js": "Vue.js",
    "tsconfig.json": "TypeScript", ".github/workflows": "GitHub Actions (CI)",
}

# Files worth reading in full when picking "key files" for the AI
PRIORITY_FILENAMES = {
    "readme.md", "readme", "main.py", "app.py", "index.js", "index.ts",
    "package.json", "requirements.txt", "pyproject.toml", "setup.py",
    "__init__.py", "cli.py",
}


def parse_repo_url(url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a GitHub URL or 'owner/repo' shorthand."""
    url = url.strip().rstrip("/")
    match = re.search(r"github\.com/([^/]+)/([^/]+)", url)
    if match:
        owner, repo = match.group(1), match.group(2)
    elif "/" in url and " " not in url:
        owner, repo = url.split("/", 1)
    else:
        raise ValueError(f"Could not parse a GitHub owner/repo from: {url}")
    return owner, repo.removesuffix(".git")


def _get(url: str) -> dict:
    resp = requests.get(url, timeout=15, headers=_auth_headers())
    if resp.status_code == 403 and "rate limit" in resp.text.lower():
        if os.environ.get("GITHUB_TOKEN"):
            raise RuntimeError("GitHub API rate limit hit even with a token set. Wait a bit and try again.")
        raise RuntimeError(
            "GitHub API rate limit hit (60 req/hour without auth, shared across your whole network). "
            "Add GITHUB_TOKEN=ghp_your_token to your .env file to raise this to 5,000 req/hour -- "
            "generate one at https://github.com/settings/tokens (no scopes needed for public repos)."
        )
    if resp.status_code == 404:
        raise RuntimeError(f"Repository not found (404): {url}. Check the owner/repo name is correct and public.")
    resp.raise_for_status()
    return resp.json()


def fetch_repo_info(owner: str, repo: str) -> dict:
    """Basic repo metadata: description, stars, language, default branch, etc."""
    data = _get(f"{GITHUB_API}/repos/{owner}/{repo}")
    return {
        "name": data["name"],
        "full_name": data["full_name"],
        "description": data.get("description") or "(no description provided)",
        "language": data.get("language"),
        "stars": data.get("stargazers_count", 0),
        "default_branch": data.get("default_branch", "main"),
        "topics": data.get("topics", []),
        "url": data["html_url"],
    }


def fetch_file_tree(owner: str, repo: str, branch: str) -> list[dict]:
    """Full recursive file tree (path + type) for the default branch."""
    data = _get(f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1")
    return [item for item in data.get("tree", []) if item["type"] == "blob"]


def detect_tech_stack(file_tree: list[dict]) -> list[str]:
    """Heuristic tech-stack detection from file extensions and known filenames."""
    found = set()
    for item in file_tree:
        path = item["path"]
        base = path.rsplit("/", 1)[-1].lower()
        if base in TECH_BY_FILENAME:
            found.add(TECH_BY_FILENAME[base])
        for ext, label in TECH_BY_EXTENSION.items():
            if base.endswith(ext):
                found.add(label)
                break
        if path.startswith(".github/workflows"):
            found.add(TECH_BY_FILENAME[".github/workflows"])
    return sorted(found)


def top_level_folders(file_tree: list[dict]) -> dict[str, list[str]]:
    """Group file paths by their top-level folder (files at root go under '.')."""
    folders: dict[str, list[str]] = {}
    for item in file_tree:
        parts = item["path"].split("/")
        top = parts[0] if len(parts) > 1 else "."
        folders.setdefault(top, []).append(item["path"])
    return folders


def pick_key_files(file_tree: list[dict], limit: int = 8) -> list[str]:
    """Pick a small set of high-signal file paths worth sending to the AI."""
    scored = []
    for item in file_tree:
        path = item["path"]
        base = path.rsplit("/", 1)[-1].lower()
        depth = path.count("/")
        score = 0
        if base in PRIORITY_FILENAMES:
            score += 10
        if depth == 0:
            score += 3
        elif depth == 1:
            score += 1
        if "test" in path.lower():
            score -= 5
        scored.append((score, path))
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [path for score, path in scored[:limit] if score > 0]


def fetch_file_content(owner: str, repo: str, branch: str, path: str, max_chars: int = 3000) -> str:
    """Fetch raw file content, truncated so we never ship an entire large file to the AI."""
    resp = requests.get(f"{RAW_BASE}/{owner}/{repo}/{branch}/{path}", timeout=15)
    if resp.status_code != 200:
        return ""
    text = resp.text
    if len(text) > max_chars:
        text = text[:max_chars] + "\n... [truncated]"
    return text
