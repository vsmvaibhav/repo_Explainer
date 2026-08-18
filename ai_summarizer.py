"""
ai_summarizer.py
-----------------
Sends a compact bundle (file names + a handful of key file contents --
never the whole repo) to Groq's API and asks it to produce the
human-readable explanation sections of the report.
"""

import json
import os

from groq import Groq

DEFAULT_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")

SYSTEM_PROMPT = (
    "You are a senior software engineer writing an onboarding guide for a "
    "new developer joining a codebase. Be precise, concrete, and concise. "
    "Only use the file names and file contents given to you -- do not invent "
    "files, functions, or behavior you cannot see. Respond with valid JSON only."
)


def _client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to a .env file in this folder, e.g.\n"
            "  GROQ_API_KEY=gsk_your_key_here"
        )
    return Groq(api_key=api_key)


def _build_prompt(repo_info: dict, folders: dict, key_file_contents: dict, tech_stack: list) -> str:
    folder_listing = "\n".join(
        f"- {folder}/ ({len(paths)} files): " + ", ".join(paths[:6]) + ("..." if len(paths) > 6 else "")
        for folder, paths in sorted(folders.items())
    )
    files_section = "\n\n".join(
        f"### {path}\n```\n{content}\n```" for path, content in key_file_contents.items() if content
    )
    return f"""Repository: {repo_info['full_name']}
Description: {repo_info['description']}
Primary language (GitHub-detected): {repo_info['language']}
Detected tech stack (heuristic): {', '.join(tech_stack) or 'unknown'}

Top-level folder structure:
{folder_listing}

Contents of the most important files:
{files_section}

Return JSON with exactly these keys:
- "summary": one paragraph (3-5 sentences) explaining what this project does and how it works.
- "folder_explanations": an object mapping each top-level folder name (use "." for root) to a
  one-sentence explanation of its purpose.
- "top_files": a list of up to 3 objects, each {{"path": "...", "why": "one sentence"}},
  naming the most important files a new developer should read first.
- "improvement": one concrete, specific suggested improvement for this codebase (1-2 sentences).
"""


def summarize_project(repo_info: dict, folders: dict, key_file_contents: dict, tech_stack: list) -> dict:
    """Call Groq to get the summary, folder explanations, top files, and improvement."""
    client = _client()
    prompt = _build_prompt(repo_info, folders, key_file_contents, tech_stack)
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def generate_interview_questions(repo_info: dict, summary: dict) -> list[str]:
    """Call Groq for 5 questions an interviewer might ask about this codebase."""
    client = _client()
    prompt = f"""Repository: {repo_info['full_name']}
Summary: {summary.get('summary', '')}
Suggested improvement noted: {summary.get('improvement', '')}

Generate 5 interview questions a technical interviewer might ask a candidate
who built or deeply studied this codebase. Mix architecture, trade-off, and
"why did you do X instead of Y" style questions. Return JSON with exactly
one key: "questions", a list of 5 strings."""
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.5,
        response_format={"type": "json_object"},
    )
    data = json.loads(response.choices[0].message.content)
    return data.get("questions", [])
