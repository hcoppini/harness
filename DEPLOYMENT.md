# HARNESS // Cross-Device Deployment & Laptop Setup Guide

Harness is built to work seamlessly across your **Desktop PC**, your **Laptop on the go**, and your **iPhone (PWA)**.

---

## 1. Instant Vercel Cloud Deployment (Access from Any Browser)

Harness is configured for **zero-config Python Serverless deployment on Vercel**.

1. When you push to GitHub (`main` or `master`), Vercel automatically deploys via `@vercel/python`.
2. Visit your Vercel deployment URL (e.g. `https://harness-xxxx.vercel.app`):
   - **On your Laptop**: Open the URL in Chrome, Brave, Edge, or Safari. All 6 layers (Dashboard, Today, TUM Metro, Projects, Body, Knowledge) work directly in the browser with full REST and RPC capability.
   - **On your iPhone**: Open the URL in Safari $\to$ Tap **Share** $\to$ **"Add to Home Screen"** to install Harness as a full-screen standalone PWA.

---

## 2. Running Directly on Your Laptop (Offline / Native)

If you want to run Harness locally on your laptop without an internet connection:

1. **Clone or pull the repo on your laptop**:
   ```bash
   git clone https://github.com/hcoppini/harness.git
   cd harness
   ```
2. **Install dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```
3. **Run Harness**:
   - **Native Desktop App**: Double-click `run.bat` or run:
     ```bash
     python main.py
     ```
   - **Local Web Server**:
     ```bash
     python server.py
     ```
     (Open `http://localhost:5000` in any browser).

---

## 3. Alternative Cloud Deployments

### Deploy on Render.com (Free Tier)
1. In [Render.com](https://render.com), create a **Web Service** connected to your `harness` repo.
2. Build command: `pip install -r requirements.txt gunicorn`
3. Start command: `python server.py`

### Deploy on Railway.app (Free Tier)
1. In [Railway.app](https://railway.app), create a new project from your GitHub repo.
2. Railway will automatically pick up the `Procfile` (`web: gunicorn server:app`).

---

## 4. Cross-Device Sync Status

- Click the **Sync Badge** in the top right header of the app (`Synced`) to trigger instant synchronization.
- JSON configurations can also be exported and imported via the **JSON Hub** button in the header.
