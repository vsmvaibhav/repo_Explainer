#!/usr/bin/env python3
"""
RepoLens web app -- a thin Flask wrapper around the existing CLI pipeline
(github_client -> ai_summarizer -> report_generator). Reuses the same
modules main.py uses, so the CLI and the website always stay in sync.
"""

import os

import markdown as md
from dotenv import load_dotenv
from flask import Flask, render_template, request

from github_client import (
    parse_repo_url, fetch_repo_info, fetch_file_tree,
    detect_tech_stack, top_level_folders, pick_key_files, fetch_file_content,
)
from ai_summarizer import summarize_project, generate_interview_questions
from report_generator import build_markdown

load_dotenv()

app = Flask(__name__)

# Rate limiting -- deploying this makes it a public URL, so cap usage per IP
# to keep GitHub/Groq API costs and quotas bounded. See requirements.txt.
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    limiter = Limiter(get_remote_address, app=app, default_limits=["20 per hour"])
except ImportError:
    limiter = None  # app still works locally without flask-limiter installed


def run_pipeline(repo_url: str, interview: bool) -> str:
    """Same steps as main.py's CLI, returning the finished markdown report."""
    owner, repo = parse_repo_url(repo_url)
    repo_info = fetch_repo_info(owner, repo)

    file_tree = fetch_file_tree(owner, repo, repo_info["default_branch"])
    tech_stack = detect_tech_stack(file_tree)
    folders = top_level_folders(file_tree)

    key_paths = pick_key_files(file_tree)
    key_file_contents = {
        path: fetch_file_content(owner, repo, repo_info["default_branch"], path)
        for path in key_paths
    }

    ai_result = summarize_project(repo_info, folders, key_file_contents, tech_stack)

    interview_questions = None
    if interview:
        interview_questions = generate_interview_questions(repo_info, ai_result)

    return build_markdown(repo_info, tech_stack, ai_result, interview_questions), repo_info


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    repo_url = request.form.get("repo_url", "").strip()
    interview = request.form.get("interview") == "on"

    if not repo_url:
        return render_template("index.html", error="Please enter a GitHub repo URL."), 400

    try:
        report_md, repo_info = run_pipeline(repo_url, interview)
    except Exception as exc:
        return render_template("index.html", error=str(exc), repo_url=repo_url), 400

    report_html = md.markdown(report_md, extensions=["fenced_code", "tables"])
    return render_template(
        "result.html", report_html=report_html, report_md=report_md, repo_info=repo_info
    )


if __name__ == "__main__":
    # Local dev only. In production, Render runs this via gunicorn (see Procfile).
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
