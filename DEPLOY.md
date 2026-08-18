# Deploying RepoLens to Render

This turns your local `python main.py` CLI into a public website at a URL
like `https://repolens.onrender.com`, using the same pipeline code
(`github_client.py`, `ai_summarizer.py`, `report_generator.py`) behind a
small Flask app (`app.py`).

## 0. Test it locally first

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000, paste a repo URL, click Generate. Confirm it
works before deploying -- easier to debug locally than on Render.

## 1. Push the project to GitHub

Render deploys from a GitHub repo, so this needs to be in one.

```bash
cd repo-explainer
git init                              # skip if already a git repo
git add .
git commit -m "Add Flask web app for RepoLens"
```

Create a new repo on GitHub (Repolens or similar), then:

```bash
git remote add origin https://github.com/<your-username>/repo-explainer.git
git branch -M main
git push -u origin main
```

**Double-check `.env` is NOT in this commit** -- run `git status` and make
sure it's not listed (it's in `.gitignore`, so it shouldn't be, but worth
a glance). Your API keys must never end up in a public GitHub repo.

## 2. Create the Render web service

1. Go to [render.com](https://render.com) and sign up / log in (you can
   sign in with your GitHub account, which also makes step 3 easier).
2. Click **New +** -> **Web Service**.
3. Connect your GitHub account if prompted, then select the
   `repo-explainer` repository you just pushed.
4. Render should auto-detect it's a Python app. Fill in / confirm:
   - **Name**: `repolens` (or anything -- this becomes part of your URL)
   - **Region**: whichever is closest to you
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --timeout 60`
   - **Instance Type**: **Free**

   (If Render picks up `render.yaml` from the repo automatically, most of
   this is pre-filled for you.)

## 3. Add your API keys as environment variables

This is the important part -- your `.env` file never gets pushed to
GitHub, so Render doesn't have your keys yet. In the Render dashboard for
this service:

1. Go to the **Environment** tab.
2. Add two environment variables:
   - `GROQ_API_KEY` = your real Groq key
   - `GITHUB_TOKEN` = your real GitHub token
3. Save. Render will redeploy automatically when you add env vars.

## 4. Deploy

Click **Create Web Service** (or **Deploy** if you already created it).
Render will install dependencies and start the app. Watch the **Logs**
tab -- when you see something like `Booting worker` with no errors, it's
live.

Your site will be at `https://<name-you-chose>.onrender.com`.

## 5. Verify

Open the URL, paste a repo like `https://github.com/pallets/flask`, and
generate a report. First request after idle time will be slow (see the
cold-start note below) -- that's expected.

## Things to know about Render's free tier

- **Spins down after 15 minutes of inactivity.** The next request after
  that wakes it back up, which takes 30-60 seconds. Fine for a portfolio
  demo link, just don't expect instant response on the first visit.
- **750 free instance-hours/month**, shared across all your free services
  -- plenty for a low-traffic personal project.
- Every `git push` to `main` auto-redeploys, so updates are just:
  ```bash
  git add .
  git commit -m "tweak something"
  git push
  ```

## Keeping it from costing you money or hitting quotas

Even though you said this is mainly for your own demo, once it's
deployed the URL is technically public. Two things are already in place
to protect you:

- **Flask-Limiter caps each visitor to 20 report generations/hour** (see
  `app.py`) -- prevents one visitor (or a bot) from burning through your
  Groq quota or your GitHub token's 5,000 req/hour limit.
- Both the Groq key and GitHub token live only in Render's environment
  variables, never in the repo or in the client-side HTML.

If you want it locked down further (e.g. only you can use it), the
simplest option is to add a shared password check in `app.py` -- say the
word and I'll add that.

## Updating the site later

Any time you change code locally:

```bash
git add .
git commit -m "describe the change"
git push
```

Render picks it up and redeploys within a minute or two.
