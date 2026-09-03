# HARNESS // iPhone Companion & Cloud Sync Deployment Guide

Harness includes a companion Progressive Web App (PWA) tailored for **iOS Safari**. Any checkbox ticked, task added, or workout logged on your iPhone synchronizes with your central database.

---

## Option 1: 1-Click Free Cloud Deployment (Recommended for 24/7 Access)

### Deploy on Render.com (Free Tier)
1. Push your Harness repository to your GitHub account (Private or Public).
2. Go to [Render.com](https://render.com) and create a free account.
3. Click **New +** $\to$ **Web Service** $\to$ Connect your `harness` repository.
4. Render will automatically detect `render.yaml` or you can set:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt gunicorn`
   - **Start Command**: `python server.py`
5. Click **Deploy Web Service**.
6. Once deployed, Render gives you a free HTTPS URL: `https://harness-xxxx.onrender.com`.

### Deploy on Railway.app (Free Tier)
1. Go to [Railway.app](https://railway.app) $\to$ **New Project** $\to$ **Deploy from GitHub repo**.
2. Railway detects the `Procfile` and launches the server.

---

## Option 2: Zero-Cost Cloudflare Tunnel (Run from your PC)

If your PC is on and you want instant access to your exact local database without uploading to a third-party cloud:

1. Download the free [Cloudflare Tunnel CLI (`cloudflared`)](https://github.com/cloudflare/cloudflared/releases).
2. In terminal, run:
   ```bash
   python server.py
   ```
3. In a second terminal window, run:
   ```bash
   cloudflared tunnel --url http://localhost:5000
   ```
4. Cloudflare outputs a secure public HTTPS URL (e.g. `https://xxxx-xxxx.trycloudflare.com`).
5. Open that URL on your iPhone Safari!

---

## How to Install the iPhone PWA to your Home Screen

1. Open your deployed URL on your **iPhone in Safari** (e.g., `https://your-harness-url.com/mobile` or `https://your-harness-url.com`).
2. Tap the **Share button** (the square with an arrow pointing up at the bottom of Safari).
3. Scroll down and tap **"Add to Home Screen"** (+ icon).
4. Tap **Add** in the top right corner.
5. Harness is now installed as an app on your iPhone home screen!
   - Opens in full-screen standalone mode with no Safari URL bar.
   - Live two-way sync for Today routines, tasks, TUM deliverables, and Gym lifts.
