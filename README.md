# RepoLens — GitHub Repo Explainer CLI

Point RepoLens at any public GitHub repository and it generates a
beginner-friendly markdown report: what the project does, the tech stack,
a folder-by-folder breakdown, the 3 files to read first, and one concrete
suggested improvement. Add `--interview` and it also generates 5 questions
an interviewer might ask about the codebase.

Built as a resume/portfolio project to demonstrate the ability to read and
explain someone else's code — a core skill for interns and new hires that
most "todo app" projects don't show.

## How it works

1. Fetches repo metadata and the full file tree from the public GitHub API
   (no authentication needed for public repos).
2. Detects the tech stack from file extensions and known config files
   (`requirements.txt`, `package.json`, `go.mod`, etc.).
3. Picks a small set of high-signal files (README, entry points, config
   files — never the whole repo) and sends **only their names and
   contents**, not the entire codebase, to the AI.
4. [Groq](https://console.groq.com) (fast open-weight LLM inference) turns
   that bundle into the summary, folder explanations, top files, and
   improvement suggestion.
5. Everything is assembled into a single markdown report.

## Installation

```bash
git clone <this-repo-url> repo-explainer
cd repo-explainer
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
```

## Setup

1. Get a free API key at [console.groq.com](https://console.groq.com).
2. Copy the example env file and add your key:

```bash
cp .env.example .env
# then edit .env and set GROQ_API_KEY=gsk_your_real_key
```

The key is loaded from `.env` automatically (via `python-dotenv`) and is
never sent anywhere except Groq's API. `.env` is git-ignored.

### GitHub rate limit (recommended)

Without a token, the GitHub API allows only 60 requests/hour, **shared
across your entire network** (Wi-Fi, VPN, whatever else is on the same
IP) -- easy to hit after just a couple of runs. Fix this by adding a
personal access token:

1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
   -> **Generate new token (classic)**.
2. Give it any name, leave every scope checkbox unchecked (no permissions
   needed to read public repos), and generate it.
3. Add it to `.env`:

```
GITHUB_TOKEN=ghp_your_token_here
```

This raises the limit to 5,000 requests/hour.

## Usage

```bash
python main.py https://github.com/owner/repo
python main.py owner/repo                       # shorthand also works
python main.py owner/repo --interview            # + 5 interview questions
python main.py owner/repo -o my_report.md        # custom output filename
```

## Web app

There's also a small Flask front end (`app.py`) that wraps the exact same
pipeline in a one-page website: paste a repo URL, get the rendered
report in the browser.

```bash
python app.py
# open http://localhost:5000
```

To put it online, see [DEPLOY.md](DEPLOY.md) for a step-by-step guide to
deploying it on Render for free.

## Example output

```markdown
# Repo Explainer: octocat/Hello-World

## 1. Summary
This project is a minimal example repository used to demonstrate basic
GitHub workflows...

## 2. Tech Stack Detected
- Python
- GitHub Actions (CI)

## 3. Folder-by-Folder Explanation
- **/ (root)** -- Root config and entry point.
- **`src/`** -- Core application logic.

## 4. Three Most Important Files to Read First
1. **`main.py`** -- Entry point that wires the CLI together.
2. **`README.md`** -- Explains what the project does and how to run it.

## 5. Suggested Improvement
Add type hints and a test suite for the src/ package.
```

## Demo

![demo](docs/demo.gif)
*(placeholder — record a short terminal GIF of `python main.py <repo> --interview` and drop it at `docs/demo.gif`)*

## Project structure

```
repo-explainer/
├── main.py              # CLI entrypoint — argparse + orchestration
├── app.py                # Flask web app — same pipeline, browser UI
├── github_client.py      # GitHub API: fetch tree, detect tech stack, pick key files
├── ai_summarizer.py       # Groq API calls: summary, folders, top files, interview Qs
├── report_generator.py    # Assembles everything into the final markdown
├── templates/             # Flask HTML templates (index, result)
├── static/style.css       # Web app styling
├── Procfile               # Render/Heroku-style process declaration
├── render.yaml             # Render Blueprint (optional one-click config)
├── DEPLOY.md               # Step-by-step Render deployment guide
├── requirements.txt
├── .env.example
└── .gitignore
```

## Constraints this project respects

- Under ~400 lines total across 4 small, single-purpose modules.
- Never sends a whole repository to the AI — only file names plus a
  capped, truncated set of key file contents.
- No GitHub authentication required for public repos (subject to the
  unauthenticated rate limit of 60 requests/hour per IP).

## Notes on the AI model

The default model is `openai/gpt-oss-20b` on Groq. Override it by setting
`GROQ_MODEL` in `.env` if you want to try a different model — check
[console.groq.com/docs/models](https://console.groq.com/docs/models) for
the current list, since available models change over time.

## Resume line

> Built a Python CLI that analyses any public GitHub repository via the
> GitHub API and generates AI-powered onboarding reports (architecture
> summary, tech stack, reading guide) in under 400 lines.
