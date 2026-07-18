# Deploying VectraCore for $0

This gets your app live on the public internet for free, on a URL anyone
can visit — no server of your own, no card required.

## 0. What changed in your code

- `app.py` now also serves your frontend pages (`public/index.html`,
  `public/work.html`, etc.) from the same Flask app, at the same origin.
  Your existing JS already assumes this (`API_BASE_URL =
  window.location.origin`), so nothing else needs to change there.
- Added `requirements.txt`, `render.yaml`, `.env.example`.
- Fixed the local run command to bind `0.0.0.0` instead of `127.0.0.1`
  (127.0.0.1 refuses outside connections — it would look "broken" on any
  host even if the app started fine).

You still need to add your `prompts/` folder (`vip_prompt.py`,
`default_prompt.py`, `pro_prompt.py`) next to `app.py` — it wasn't part of
what you uploaded here.

## 1. Put the code on GitHub (free)

1. Create a free GitHub account if you don't have one.
2. Create a new **public or private** repo, e.g. `vectracore`.
3. Upload this whole folder to it (drag-and-drop on github.com works, or
   `git init && git add . && git commit -m "init" && git push`).
4. **Do NOT commit a real `.env` file.** Only `.env.example` should be in
   the repo — your actual keys go into Render's dashboard in step 3.

## 2. Create a free Render account

Go to https://render.com and sign up (GitHub login is easiest).

## 3. Deploy the web service

1. Click **New +** → **Web Service**.
2. Connect your GitHub repo.
3. Render should auto-detect `render.yaml`. If not, set manually:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
   - **Instance type:** Free
4. Under **Environment**, add the secret values Render left blank
   (`sync: false` in render.yaml means "you type this in yourself"):
   `GEMINI_API_KEY`, `ADMIN_SECRET_KEY`, `FINNHUB_KEY`, `SMTP_USER`,
   `SMTP_PASSWORD`, `FROM_EMAIL`.
5. Click **Deploy**. First deploy takes a few minutes.

When it's done, Render gives you a live URL like:

```
https://vectracore.onrender.com
```

That is a real, public, free address — anyone in the world can open it
right now. This satisfies "publish it on the internet" completely, with
no domain purchase needed.

## 4. Free tier behavior to expect

- The free plan **spins down after ~15 minutes of no traffic** and takes
  10-30 seconds to wake back up on the next request. Fine for a beta;
  annoying for users who hate the first-load delay.
- **Your `data/*.json` files (users, usage, history, feedback) do not
  persist** across redeploys/restarts on the free plan — the disk resets.
  Treat this launch as a public beta with resettable data, not permanent
  storage. If that becomes a problem, the fix later is a real database
  (Render's free Postgres tier, or similar) — not a code rewrite, just
  swapping where `_load_json`/`_save_json` read and write.

## 5. Making it feel like "your own domain" (still $0)

A real custom domain (`vectracore.com`) costs money to register — there's
no reputable way around that. But you have two free-feeling options:

**Option A — just use the Render URL.** `vectracore.onrender.com` is
already public, permanent, and free. Simplest, zero extra steps.

**Option B — free custom subdomain via is-a.dev.** Services like
https://www.is-a.dev let developers claim a free subdomain
(`vectracore.is-a.dev`) by submitting a small JSON file as a GitHub pull
request. Once merged (usually within a day or two), you set a CNAME
record pointing it at your `onrender.com` address, and Render's free tier
supports custom domains/CNAMEs. It reads better than a `.onrender.com`
URL but takes a bit of manual setup and review time.

Either way, no purchase is required to have a working, public, shareable
link today.
