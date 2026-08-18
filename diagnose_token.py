#!/usr/bin/env python3
"""
diagnose_token.py -- run this to figure out why GITHUB_TOKEN is getting a 401.
It never prints your full token, only whether it loaded and its prefix/length.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.environ.get("GITHUB_TOKEN")

print("=== .env loading ===")
if token is None:
    print("GITHUB_TOKEN is NOT set / .env was not found or the line wasn't picked up.")
    print("Checks:")
    print("  1. Is the file literally named '.env' (not '.env.txt')? On Windows,")
    print("     File Explorer often hides the real extension -- open a terminal and run:")
    print("     dir /a  (look for '.env' with no extra extension)")
    print("  2. Are you running 'python main.py' from inside the repo-explainer folder")
    print("     (the same folder that contains .env)?")
    raise SystemExit(1)

stripped = token.strip().strip('"').strip("'")
print(f"GITHUB_TOKEN loaded. length={len(token)}, prefix={token[:8]!r}")
if token != stripped:
    print("WARNING: token has leading/trailing whitespace or quote characters -- "
          "remove them from .env (no quotes, no spaces around the '=').")
if not (token.startswith("ghp_") or token.startswith("github_pat_")):
    print("WARNING: token doesn't start with 'ghp_' (classic) or 'github_pat_' "
          "(fine-grained). Did you paste the whole thing correctly?")

print("\n=== Live API test ===")
resp = requests.get(
    "https://api.github.com/repos/pallets/flask",
    headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}"},
    timeout=15,
)
print(f"Status: {resp.status_code}")
print(f"Body: {resp.text[:300]}")

if resp.status_code == 401:
    print("\n-> 401 means GitHub rejected the token itself. Likely causes:")
    print("   - Token was revoked/expired (classic tokens can be set to auto-expire).")
    print("   - If it's a FINE-GRAINED token: fine-grained tokens default to NO access.")
    print("     You must explicitly set 'Public Repositories (read-only)' under")
    print("     Repository access when creating it, or use a classic token instead.")
    print("   - Re-generate a CLASSIC token at https://github.com/settings/tokens")
    print("     -> 'Generate new token (classic)' -> leave all scope boxes unchecked.")
elif resp.status_code == 200:
    print("\n-> GitHub token works!")

print("\n=== GROQ_API_KEY check ===")
groq_key = os.environ.get("GROQ_API_KEY")
if groq_key is None:
    print("GROQ_API_KEY is NOT set in .env.")
else:
    groq_stripped = groq_key.strip().strip('"').strip("'")
    print(f"GROQ_API_KEY loaded. length={len(groq_key)}, prefix={groq_key[:8]!r}")
    if groq_key != groq_stripped:
        print("WARNING: key has leading/trailing whitespace or quote characters.")
    if not groq_key.startswith("gsk_"):
        print("WARNING: key doesn't start with 'gsk_' -- check for a duplicated prefix,")
        print("         e.g. 'gsk_gsk_...' from pasting over the .env.example line.")
    # count how many times 'gsk_' appears -- a duplicated-prefix bug shows up as 2+
    if groq_key.count("gsk_") > 1:
        print(f"WARNING: 'gsk_' appears {groq_key.count('gsk_')} times in the key -- "
              "this is almost certainly a duplicated prefix. Fix the .env line so it "
              "reads GROQ_API_KEY=gsk_<rest of your real key>, with 'gsk_' only once.")

    from groq import Groq
    try:
        client = Groq(api_key=groq_key)
        client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=5,
        )
        print("-> Groq key works!")
    except Exception as e:
        print(f"-> Groq call failed: {e}")
