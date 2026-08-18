#!/usr/bin/env python3
"""
RepoLens -- GitHub Repo Explainer CLI

Point it at any public GitHub repo URL and it generates a markdown report:
project summary, tech stack, folder-by-folder breakdown, the 3 files to
read first, and one suggested improvement. Add --interview for 5 bonus
interview questions about the codebase.

Usage:
    python main.py https://github.com/owner/repo
    python main.py owner/repo --interview
    python main.py owner/repo -o report.md
"""

import argparse
import sys

from dotenv import load_dotenv

from github_client import (
    parse_repo_url, fetch_repo_info, fetch_file_tree,
    detect_tech_stack, top_level_folders, pick_key_files, fetch_file_content,
)
from ai_summarizer import summarize_project, generate_interview_questions
from report_generator import build_markdown


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Explain a public GitHub repo in plain English.")
    parser.add_argument("repo", help="GitHub repo URL or 'owner/repo' shorthand")
    parser.add_argument("--interview", action="store_true", help="also generate 5 interview questions")
    parser.add_argument("-o", "--output", default="REPORT.md", help="output markdown file (default: REPORT.md)")
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()

    try:
        owner, repo = parse_repo_url(args.repo)
        print(f"Fetching {owner}/{repo} from GitHub...")
        repo_info = fetch_repo_info(owner, repo)

        print("Reading file tree...")
        file_tree = fetch_file_tree(owner, repo, repo_info["default_branch"])
        tech_stack = detect_tech_stack(file_tree)
        folders = top_level_folders(file_tree)

        key_paths = pick_key_files(file_tree)
        print(f"Reading {len(key_paths)} key files: {', '.join(key_paths) or '(none found)'}")
        key_file_contents = {
            path: fetch_file_content(owner, repo, repo_info["default_branch"], path)
            for path in key_paths
        }

        print("Asking the AI to summarize the codebase...")
        ai_result = summarize_project(repo_info, folders, key_file_contents, tech_stack)

        interview_questions = None
        if args.interview:
            print("Generating interview questions...")
            interview_questions = generate_interview_questions(repo_info, ai_result)

        report = build_markdown(repo_info, tech_stack, ai_result, interview_questions)

    except Exception as exc:  # surfaced to the user with a clean message, not a stack trace
        print(f"\nError: {exc}", file=sys.stderr)
        return 1

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nDone. Report written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
