"""
Headless Cloud Vulcan Synchronizer for Harness (GitHub Actions & Serverless).
Runs autonomously on scheduled cron triggers (8:00 AM, 2:00 PM, 5:00 PM Polish time).
Connects to Supabase, pulls student credentials, polls Vulcan UONET+ HebeCE API,
and replicates updated exams, homework, and grades directly to Supabase Cloud.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.db import init_db, get_connection, DATA_DIR
from app.services import vulcan_service, sync_service


def get_cloud_supabase_creds():
    """Resolves Supabase URL and Key from environment variables or sync_config.json."""
    url = (
        os.environ.get("SUPABASE_URL")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
        or os.environ.get("EXPO_PUBLIC_SUPABASE_URL")
    )
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_KEY")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY")
        or os.environ.get("SUPABASE_PUBLISHABLE_KEY")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
    )

    if not url or not key:
        cfg = sync_service.get_sync_config()
        url = url or cfg.get("supabase_url")
        key = key or cfg.get("supabase_key")

    return (url.strip().rstrip("/") if url else "", key.strip() if key else "")


def fetch_vulcan_config_from_supabase(supabase_url: str, supabase_key: str):
    """Pulls stored vulcan_config from Supabase app_settings table."""
    if not supabase_url or not supabase_key:
        return None

    endpoint = f"{supabase_url}/rest/v1/app_settings?key=eq.vulcan_config&select=*"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept": "application/json",
    }
    req = urllib.request.Request(endpoint, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and isinstance(data, list) and len(data) > 0:
                raw_val = data[0].get("value")
                if isinstance(raw_val, dict):
                    return raw_val
                elif isinstance(raw_val, str):
                    try:
                        return json.loads(raw_val)
                    except Exception:
                        return None
    except Exception as e:
        print(f"[Cloud Sync] Supabase app_settings fetch notice: {e}")
    return None


def run_cloud_sync():
    """Main headless execution entry point."""
    timestamp = datetime.now().isoformat()
    print(f"[{timestamp}] === Starting Harness Headless Cloud Vulcan Sync ===")

    # 1. Resolve Supabase credentials
    sb_url, sb_key = get_cloud_supabase_creds()
    if sb_url and sb_key:
        print(f"[Cloud Sync] Supabase connected: {sb_url[:24]}...")
        # Populate sync_service config in environment/memory
        os.environ["SUPABASE_URL"] = sb_url
        os.environ["SUPABASE_KEY"] = sb_key
    else:
        print("[Cloud Sync] WARNING: Supabase credentials not found in env or config.")

    # 2. Resolve Vulcan configuration
    vulcan_cfg = None
    env_v_json = os.environ.get("VULCAN_CONFIG_JSON")
    if env_v_json:
        try:
            vulcan_cfg = json.loads(env_v_json)
            print("[Cloud Sync] Loaded vulcan_config from VULCAN_CONFIG_JSON env.")
        except Exception as e:
            print(f"[Cloud Sync] Error parsing VULCAN_CONFIG_JSON: {e}")

    if not vulcan_cfg and sb_url and sb_key:
        vulcan_cfg = fetch_vulcan_config_from_supabase(sb_url, sb_key)
        if vulcan_cfg:
            print(f"[Cloud Sync] Loaded vulcan_config from Supabase app_settings (Student: {vulcan_cfg.get('student_name')}).")

    if not vulcan_cfg:
        local_cfg = vulcan_service.get_vulcan_config()
        if local_cfg.get("registered_device"):
            vulcan_cfg = local_cfg
            print(f"[Cloud Sync] Using local vulcan_config.json (Student: {local_cfg.get('student_name')}).")

    if vulcan_cfg:
        # Save to local runner workspace so vulcan_service uses it
        vulcan_service.save_vulcan_config(vulcan_cfg)
    else:
        print("[Cloud Sync] WARNING: No registered Vulcan device configuration found.")

    # 3. Ensure runner database tables are initialized
    init_db()
    conn = get_connection()

    # 4. Fetch live Vulcan data and ingest into SQLite
    sync_result = vulcan_service.sync_vulcan_data(force_refresh=True, conn=conn)
    print(f"[Cloud Sync] Vulcan Ingestion Result: {sync_result}")

    # 5. Push updated data to Supabase
    replicated = {"exams": 0, "homework": 0, "grades": 0, "grade_entries": 0}
    if sb_url and sb_key:
        try:
            replicated["exams"] = sync_service.sync_school_exams(conn)
            replicated["homework"] = sync_service.sync_homework_items(conn)
            replicated["grades"] = sync_service.sync_tum_grades(conn)
            replicated["grade_entries"] = sync_service.sync_tum_grade_entries(conn)
            print(f"[Cloud Sync] Replicated to Supabase: {replicated}")

            # Update last_synced_at in app_settings
            now_str = datetime.now().isoformat()
            sync_service.upsert_remote_item("app_settings", "key", {
                "key": "last_vulcan_cloud_sync",
                "value": json.dumps({"timestamp": now_str, "status": "success", "replicated": replicated}),
            })
        except Exception as e:
            print(f"[Cloud Sync] Error replicating to Supabase: {e}")

    conn.close()
    print(f"[{datetime.now().isoformat()}] === Cloud Vulcan Sync Completed Successfully ===")
    return {
        "status": "success",
        "vulcan_result": sync_result,
        "supabase_replicated": replicated,
    }


if __name__ == "__main__":
    res = run_cloud_sync()
    sys.exit(0)
