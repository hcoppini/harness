"""
Google Calendar Bidirectional Sync Service for Harness Executive OS.

Supports:
- Dual sync modes:
  1. Full Google OAuth 2.0 (Desktop PKCE loopback + Web callback) using Calendar v3 REST API
  2. Zero-config iCal fallback (Private Google Calendar .ics pull + RFC 5545 /api/calendar.ics live feed)
- Exact test/exam-to-TM1 school lesson time matching
- Conflict capture & user-override detection via `gcal_sync_map`
- Tagged `[Test]` / `Sprawdzian` / `Kartkówka` import from Google Calendar -> `school_exams`
- Zero-dependency Europe/Warsaw CET/CEST timezone calculation (Windows Python safe)
"""

from __future__ import annotations

import base64
import calendar
import datetime as dt
import hashlib
import http.server
import ipaddress
import json
import os
import re
import secrets
import sqlite3
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.db import get_connection


def _http_call(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    form_data: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 20,
) -> Tuple[int, str]:
    """Zero-dependency HTTP client backed by stdlib `urllib.request`."""
    full_url = url
    if params:
        qs = urllib.parse.urlencode(params, doseq=True)
        sep = "&" if "?" in full_url else "?"
        full_url = f"{full_url}{sep}{qs}"

    hdrs = dict(headers or {})
    data_bytes: Optional[bytes] = None
    if json_body is not None:
        data_bytes = json.dumps(json_body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    elif form_data is not None:
        data_bytes = urllib.parse.urlencode(form_data).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded")

    req = urllib.request.Request(full_url, data=data_bytes, headers=hdrs, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as err:
        body = ""
        try:
            body = err.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return int(err.code), body

DATA_DIR = Path(os.environ.get("HARNESS_DATA_DIR") or (Path(__file__).resolve().parent.parent.parent / "data"))
CONFIG_FILE = DATA_DIR / "gcalendar_config.json"

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GCAL_API_BASE = "https://www.googleapis.com/calendar/v3"
GCAL_SCOPES = (
    "https://www.googleapis.com/auth/calendar "
    "https://www.googleapis.com/auth/userinfo.email"
)

DEFAULT_CONFIG: Dict[str, Any] = {
    "mode": "unconfigured",  # unconfigured | oauth | ical
    "client_id": "",
    "client_secret": "",
    "refresh_token": "",
    "access_token": "",
    "token_expires_at": "",
    "connected_email": "",
    "target_calendar_id": "",
    "target_calendar_summary": "Harness Executive OS",
    "use_dedicated_calendar": True,
    "pull_calendar_ids": ["primary"],
    "private_ical_urls": [],
    "sync_exams": True,
    "sync_homework": True,
    "sync_plan_blocks": True,
    "sync_school_timetable": True,
    "include_sleep_rest_blocks": False,
    "import_tagged_tests": True,
    "auto_optimize_schedule": True,
    "sync_horizon_days": 14,
    "ics_feed_token": "",
    "last_sync_at": "",
    "last_sync_status": "",
    "last_sync_summary": {},
    "last_error": "",
}

TEST_TAG_PATTERN = re.compile(
    r"^\s*(?:\[(?:test|exam|sprawdzian|kartk[oó]wka|quiz)\]|"
    r"(?:sprawdzian|kartk[oó]wka|egzamin|kolokwium|test)\s*[:\-–—])\s*(.+)$",
    re.IGNORECASE,
)

# In-memory OAuth PKCE sessions for loopback/web flows
_OAUTH_LOCK = threading.Lock()
_OAUTH_STATE_STORE: Dict[str, Dict[str, Any]] = {}
_LOOPBACK_STATE: Dict[str, Any] = {
    "active": False,
    "status": "idle",
    "error": "",
    "auth_url": "",
}


# ---------------------------------------------------------------------------
# Database Schema
# ---------------------------------------------------------------------------

def ensure_gcal_tables(conn: sqlite3.Connection) -> None:
    """Creates Google Calendar sync cache and ownership map tables if missing."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS gcal_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL,
            calendar_id TEXT NOT NULL DEFAULT 'primary',
            summary TEXT NOT NULL DEFAULT '',
            description TEXT DEFAULT '',
            location TEXT DEFAULT '',
            date TEXT NOT NULL,
            start_time TEXT DEFAULT '',
            end_time TEXT DEFAULT '',
            start_iso TEXT DEFAULT '',
            end_iso TEXT DEFAULT '',
            is_all_day INTEGER DEFAULT 0,
            status TEXT DEFAULT 'confirmed',
            is_harness_managed INTEGER DEFAULT 0,
            harness_kind TEXT DEFAULT '',
            harness_key TEXT DEFAULT '',
            etag TEXT DEFAULT '',
            sync_hash TEXT DEFAULT '',
            source TEXT DEFAULT 'gcal_api',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(calendar_id, event_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS gcal_sync_map (
            harness_key TEXT PRIMARY KEY,
            harness_kind TEXT NOT NULL,
            calendar_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            sync_hash TEXT DEFAULT '',
            override_date TEXT DEFAULT '',
            override_start TEXT DEFAULT '',
            override_end TEXT DEFAULT '',
            user_deleted INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gcal_events_date ON gcal_events(date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gcal_map_cal_evt ON gcal_sync_map(calendar_id, event_id)")


# ---------------------------------------------------------------------------
# Zero-Dependency Europe/Warsaw Timezone & Time Parsing
# ---------------------------------------------------------------------------

def _last_sunday_of_month(year: int, month: int) -> dt.date:
    last_day = calendar.monthrange(year, month)[1]
    d = dt.date(year, month, last_day)
    offset = (d.weekday() + 1) % 7
    return d - dt.timedelta(days=offset)


def _warsaw_offset_for_utc(utc_dt: dt.datetime) -> dt.timedelta:
    """Returns +02:00 (CEST) or +01:00 (CET) for a naive UTC datetime."""
    march_sun = _last_sunday_of_month(utc_dt.year, 3)
    oct_sun = _last_sunday_of_month(utc_dt.year, 10)
    dst_start_utc = dt.datetime.combine(march_sun, dt.time(1, 0))
    dst_end_utc = dt.datetime.combine(oct_sun, dt.time(1, 0))
    if dst_start_utc <= utc_dt < dst_end_utc:
        return dt.timedelta(hours=2)
    return dt.timedelta(hours=1)


def _warsaw_offset_for_local(local_dt: dt.datetime) -> dt.timedelta:
    """Returns +02:00 (CEST) or +01:00 (CET) for a naive local Europe/Warsaw datetime."""
    march_sun = _last_sunday_of_month(local_dt.year, 3)
    oct_sun = _last_sunday_of_month(local_dt.year, 10)
    dst_start_local = dt.datetime.combine(march_sun, dt.time(2, 0))
    dst_end_local = dt.datetime.combine(oct_sun, dt.time(3, 0))
    if dst_start_local <= local_dt < dst_end_local:
        return dt.timedelta(hours=2)
    return dt.timedelta(hours=1)


def _format_offset(td: dt.timedelta) -> str:
    total_mins = int(td.total_seconds() // 60)
    sign = "+" if total_mins >= 0 else "-"
    total_mins = abs(total_mins)
    return f"{sign}{total_mins // 60:02d}:{total_mins % 60:02d}"


def format_local_iso(date_str: str, time_str: str, tz_name: str = "Europe/Warsaw") -> str:
    """Formats YYYY-MM-DD + HH:MM into RFC 3339 ISO string with exact CET/CEST offset."""
    d = dt.date.fromisoformat(str(date_str).strip()[:10])
    parts = str(time_str).strip().split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    local_dt = dt.datetime(d.year, d.month, d.day, hour, minute, 0)

    if tz_name in ("Europe/Warsaw", "Europe/Berlin", "CET", "CEST"):
        offset = _warsaw_offset_for_local(local_dt)
        return f"{local_dt.strftime('%Y-%m-%dT%H:%M:%S')}{_format_offset(offset)}"

    try:
        from zoneinfo import ZoneInfo
        aware = local_dt.replace(tzinfo=ZoneInfo(tz_name))
        return aware.isoformat()
    except Exception:
        offset = _warsaw_offset_for_local(local_dt)
        return f"{local_dt.strftime('%Y-%m-%dT%H:%M:%S')}{_format_offset(offset)}"


def parse_time_window(time_str: str) -> Optional[Tuple[int, int]]:
    """
    Parses strings like:
      - '14:30 – 16:30'
      - '8:50- 9:35'
      - '17:20 – 20:30/21:00'
    Returns (start_minutes, end_minutes) from midnight, or None for 'All Day'/'onwards'.
    """
    if not time_str or not isinstance(time_str, str):
        return None
    m = re.match(
        r"^\s*(\d{1,2}):(\d{2})\s*[-–—]\s*(\d{1,2}):(\d{2})(?:/\d{1,2}:\d{2})?\s*$",
        time_str.strip(),
    )
    if not m:
        return None
    sh, sm, eh, em = (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
    if not (0 <= sh <= 23 and 0 <= sm <= 59 and 0 <= eh <= 24 and 0 <= em <= 59):
        return None
    start_min = sh * 60 + sm
    end_min = eh * 60 + em
    if end_min <= start_min:
        return None
    return (start_min, end_min)


def format_time_window(start_min: int, end_min: int) -> str:
    """Formats minutes since midnight into 'HH:MM – HH:MM'."""
    sh, sm = divmod(max(0, min(1439, int(start_min))), 60)
    eh, em = divmod(max(0, min(1440, int(end_min))), 60)
    return f"{sh:02d}:{sm:02d} – {eh:02d}:{em:02d}"


def _convert_utc_to_warsaw(utc_naive: dt.datetime) -> dt.datetime:
    return utc_naive + _warsaw_offset_for_utc(utc_naive)


def _parse_iso_datetime_to_warsaw(iso_str: str) -> Tuple[str, str, str]:
    """Converts RFC3339 dateTime string into local Europe/Warsaw (date, HH:MM, local_iso)."""
    raw = str(iso_str).strip()
    if raw.endswith("Z"):
        base = raw[:-1].split(".")[0]
        utc_naive = dt.datetime.strptime(base, "%Y-%m-%dT%H:%M:%S")
        local_dt = _convert_utc_to_warsaw(utc_naive)
        offset = _warsaw_offset_for_utc(utc_naive)
        return (
            local_dt.strftime("%Y-%m-%d"),
            local_dt.strftime("%H:%M"),
            f"{local_dt.strftime('%Y-%m-%dT%H:%M:%S')}{_format_offset(offset)}",
        )

    parsed = dt.datetime.fromisoformat(raw)
    if parsed.tzinfo is not None:
        utc_naive = parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
        local_dt = _convert_utc_to_warsaw(utc_naive)
        offset = _warsaw_offset_for_utc(utc_naive)
        return (
            local_dt.strftime("%Y-%m-%d"),
            local_dt.strftime("%H:%M"),
            f"{local_dt.strftime('%Y-%m-%dT%H:%M:%S')}{_format_offset(offset)}",
        )

    date_s = parsed.strftime("%Y-%m-%d")
    hm = parsed.strftime("%H:%M")
    return (date_s, hm, format_local_iso(date_s, hm))


def _today_warsaw_str() -> str:
    utc_now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    return _convert_utc_to_warsaw(utc_now).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Security & Configuration Management
# ---------------------------------------------------------------------------

def is_safe_calendar_url(url: str) -> bool:
    """Validates external calendar/iCal feed URLs (blocks file/javascript/SSRF private IPs)."""
    if not url or not isinstance(url, str):
        return False
    raw = url.strip()
    if any(ch in raw for ch in ("\r", "\n", "\x00", " ")):
        return False
    try:
        parsed = urllib.parse.urlparse(raw)
    except Exception:
        return False
    if parsed.scheme.lower() not in ("https", "http"):
        return False
    host = (parsed.hostname or "").strip().lower()
    if not host:
        return False
    if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "169.254.169.254"):
        return False
    try:
        ip_obj = ipaddress.ip_address(host)
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
            return False
    except ValueError:
        pass
    return True


def _redact_ical_url(url: str) -> str:
    """Masks embedded Google Calendar secret tokens when displaying private iCal URLs."""
    masked = re.sub(r"/(private-[^/]+)/", "/private-****/", str(url).strip())
    if masked == str(url).strip():
        parsed = urllib.parse.urlparse(masked)
        if parsed.path and len(parsed.path) > 22:
            masked = f"{parsed.scheme}://{parsed.netloc}{parsed.path[:14]}...{parsed.path[-8:]}"
    return masked


def _mask_client_id(cid: str) -> str:
    cid = (cid or "").strip()
    if len(cid) <= 14:
        return "****" if cid else ""
    return f"{cid[:8]}...{cid[-10:]}"


def get_gcalendar_config() -> Dict[str, Any]:
    """Reads `gcalendar_config.json` merged with defaults and environment overrides."""
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if CONFIG_FILE.exists():
        try:
            loaded = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                cfg.update(loaded)
        except Exception:
            pass

    # Optional environment overrides (safe for headless CI/cloud)
    if os.environ.get("GCAL_CLIENT_ID") and not cfg["client_id"]:
        cfg["client_id"] = os.environ["GCAL_CLIENT_ID"].strip()
    if os.environ.get("GCAL_CLIENT_SECRET") and not cfg["client_secret"]:
        cfg["client_secret"] = os.environ["GCAL_CLIENT_SECRET"].strip()
    if os.environ.get("GCAL_REFRESH_TOKEN") and not cfg["refresh_token"]:
        cfg["refresh_token"] = os.environ["GCAL_REFRESH_TOKEN"].strip()
        if cfg["mode"] == "unconfigured":
            cfg["mode"] = "oauth"
    if os.environ.get("GCAL_CALENDAR_ID") and not cfg["target_calendar_id"]:
        cfg["target_calendar_id"] = os.environ["GCAL_CALENDAR_ID"].strip()
    if os.environ.get("GCAL_ICS_TOKEN") and not cfg["ics_feed_token"]:
        cfg["ics_feed_token"] = os.environ["GCAL_ICS_TOKEN"].strip()
    if os.environ.get("GCAL_ICAL_URLS") and not cfg["private_ical_urls"]:
        urls = [u.strip() for u in os.environ["GCAL_ICAL_URLS"].split(",") if is_safe_calendar_url(u.strip())]
        if urls:
            cfg["private_ical_urls"] = urls
            if cfg["mode"] == "unconfigured":
                cfg["mode"] = "ical"

    # Clamp horizon and normalize lists
    try:
        cfg["sync_horizon_days"] = max(1, min(60, int(cfg.get("sync_horizon_days", 14))))
    except Exception:
        cfg["sync_horizon_days"] = 14
    if not isinstance(cfg.get("pull_calendar_ids"), list) or not cfg["pull_calendar_ids"]:
        cfg["pull_calendar_ids"] = ["primary"]
    if not isinstance(cfg.get("private_ical_urls"), list):
        cfg["private_ical_urls"] = []

    return cfg


def save_gcalendar_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Persists Google Calendar configuration cleanly to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    merged = json.loads(json.dumps(DEFAULT_CONFIG))
    if isinstance(cfg, dict):
        merged.update(cfg)
    if not merged.get("ics_feed_token"):
        merged["ics_feed_token"] = secrets.token_urlsafe(18)

    tmp_file = CONFIG_FILE.with_suffix(".tmp")
    tmp_file.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp_file, CONFIG_FILE)
    return merged


def save_gcalendar_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Updates user-editable sync preferences and iCal URLs without wiping OAuth secrets."""
    cfg = get_gcalendar_config()
    if not isinstance(settings, dict):
        return get_gcalendar_status()

    bool_keys = (
        "use_dedicated_calendar",
        "sync_exams",
        "sync_homework",
        "sync_plan_blocks",
        "sync_school_timetable",
        "include_sleep_rest_blocks",
        "import_tagged_tests",
        "auto_optimize_schedule",
    )
    for k in bool_keys:
        if k in settings:
            cfg[k] = bool(settings[k])

    str_keys = ("target_calendar_id", "target_calendar_summary")
    for k in str_keys:
        if k in settings and settings[k] is not None:
            cfg[k] = str(settings[k]).strip()

    if "sync_horizon_days" in settings:
        try:
            cfg["sync_horizon_days"] = max(1, min(60, int(settings["sync_horizon_days"])))
        except Exception:
            pass

    if "pull_calendar_ids" in settings and isinstance(settings["pull_calendar_ids"], list):
        cleaned = [str(c).strip() for c in settings["pull_calendar_ids"] if str(c).strip()]
        cfg["pull_calendar_ids"] = cleaned or ["primary"]

    if "client_id" in settings and str(settings["client_id"]).strip():
        cfg["client_id"] = str(settings["client_id"]).strip()
    if "client_secret" in settings and str(settings["client_secret"]).strip():
        cfg["client_secret"] = str(settings["client_secret"]).strip()

    if "private_ical_urls" in settings and settings["private_ical_urls"] is not None:
        raw_urls = settings["private_ical_urls"]
        if isinstance(raw_urls, str):
            raw_list = [u.strip() for u in re.split(r"[\n,]+", raw_urls) if u.strip()]
        elif isinstance(raw_urls, list):
            raw_list = [str(u).strip() for u in raw_urls if str(u).strip()]
        else:
            raw_list = []
        valid_urls = [u for u in raw_list if is_safe_calendar_url(u)]
        invalid_urls = [u for u in raw_list if not is_safe_calendar_url(u)]
        if invalid_urls:
            raise ValueError(f"Unsafe or invalid calendar URL(s): {invalid_urls[0]}")
        cfg["private_ical_urls"] = valid_urls
        if valid_urls and cfg.get("mode") == "unconfigured":
            cfg["mode"] = "ical"
        elif not valid_urls and cfg.get("mode") == "ical" and not cfg.get("refresh_token"):
            cfg["mode"] = "unconfigured"

    save_gcalendar_config(cfg)
    return get_gcalendar_status()


def import_oauth_credentials(raw_input: Any) -> Dict[str, Any]:
    """Parses Google Cloud OAuth client JSON ('installed', 'web', or flat) and saves safely."""
    try:
        data = json.loads(raw_input) if isinstance(raw_input, str) else raw_input
    except Exception as exc:
        return {"success": False, "error": f"Invalid JSON format: {exc}"}

    if not isinstance(data, dict):
        return {"success": False, "error": "Credentials JSON must be an object."}

    cred_type = "flat"
    block = data
    if isinstance(data.get("installed"), dict):
        block = data["installed"]
        cred_type = "installed"
    elif isinstance(data.get("web"), dict):
        block = data["web"]
        cred_type = "web"

    client_id = str(block.get("client_id") or "").strip()
    client_secret = str(block.get("client_secret") or "").strip()
    if not client_id:
        return {"success": False, "error": "Missing 'client_id' in credentials JSON."}

    cfg = get_gcalendar_config()
    cfg["client_id"] = client_id
    if client_secret:
        cfg["client_secret"] = client_secret
    save_gcalendar_config(cfg)

    return {
        "success": True,
        "type": cred_type,
        "client_id": client_id,
        "has_client_secret": bool(cfg["client_secret"]),
    }


def disconnect_gcalendar(clear_cache: bool = False, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """Revokes local OAuth tokens while keeping user client_id/preferences unless cleared."""
    cfg = get_gcalendar_config()
    cfg["refresh_token"] = ""
    cfg["access_token"] = ""
    cfg["token_expires_at"] = ""
    cfg["connected_email"] = ""
    cfg["mode"] = "ical" if cfg.get("private_ical_urls") else "unconfigured"
    cfg["last_error"] = ""
    save_gcalendar_config(cfg)

    if clear_cache:
        own_conn = conn is None
        if own_conn:
            conn = get_connection()
        try:
            ensure_gcal_tables(conn)
            conn.execute("DELETE FROM gcal_events")
            conn.execute("DELETE FROM gcal_sync_map")
            conn.commit()
        finally:
            if own_conn:
                conn.close()

    return get_gcalendar_status(conn=conn)


def get_gcalendar_status(conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """Returns redacted status + live DB sync counts (never leaks secrets or tokens)."""
    cfg = get_gcalendar_config()
    if not cfg.get("ics_feed_token"):
        cfg = save_gcalendar_config(cfg)

    own_conn = conn is None
    if own_conn:
        conn = get_connection()

    cached_count = 0
    mapped_count = 0
    overrides_count = 0
    upcoming_conflicts = 0
    today_s = _today_warsaw_str()
    try:
        ensure_gcal_tables(conn)
        cached_count = conn.execute(
            "SELECT COUNT(*) FROM gcal_events WHERE status != 'cancelled' AND is_harness_managed = 0"
        ).fetchone()[0]
        mapped_count = conn.execute(
            "SELECT COUNT(*) FROM gcal_sync_map WHERE user_deleted = 0"
        ).fetchone()[0]
        overrides_count = conn.execute(
            "SELECT COUNT(*) FROM gcal_sync_map WHERE override_start != '' OR override_date != '' OR user_deleted = 1"
        ).fetchone()[0]
        upcoming_conflicts = conn.execute(
            "SELECT COUNT(*) FROM gcal_events WHERE date >= ? AND status != 'cancelled' AND is_harness_managed = 0 AND is_all_day = 0",
            (today_s,),
        ).fetchone()[0]
    except Exception:
        pass
    finally:
        if own_conn:
            conn.close()

    oauth_ready = bool(cfg.get("refresh_token") or cfg.get("access_token"))
    ical_ready = bool(cfg.get("private_ical_urls"))
    connected = (cfg.get("mode") == "oauth" and oauth_ready) or (cfg.get("mode") == "ical" and ical_ready)

    with _OAUTH_LOCK:
        oauth_flow_state = dict(_LOOPBACK_STATE)

    return {
        "mode": cfg.get("mode", "unconfigured"),
        "connected": connected,
        "oauth_connected": oauth_ready and cfg.get("mode") == "oauth",
        "ical_connected": ical_ready,
        "has_client_id": bool(cfg.get("client_id")),
        "has_client_secret": bool(cfg.get("client_secret")),
        "has_refresh_token": bool(cfg.get("refresh_token")),
        "client_id_masked": _mask_client_id(cfg.get("client_id", "")),
        "connected_email": cfg.get("connected_email", ""),
        "target_calendar_id": cfg.get("target_calendar_id", ""),
        "target_calendar_summary": cfg.get("target_calendar_summary", "Harness Executive OS"),
        "use_dedicated_calendar": bool(cfg.get("use_dedicated_calendar", True)),
        "pull_calendar_ids": list(cfg.get("pull_calendar_ids", ["primary"])),
        "private_ical_count": len(cfg.get("private_ical_urls", [])),
        "private_ical_masked": [_redact_ical_url(u) for u in cfg.get("private_ical_urls", [])],
        "sync_exams": bool(cfg.get("sync_exams", True)),
        "sync_homework": bool(cfg.get("sync_homework", True)),
        "sync_plan_blocks": bool(cfg.get("sync_plan_blocks", True)),
        "sync_school_timetable": bool(cfg.get("sync_school_timetable", True)),
        "include_sleep_rest_blocks": bool(cfg.get("include_sleep_rest_blocks", False)),
        "import_tagged_tests": bool(cfg.get("import_tagged_tests", True)),
        "auto_optimize_schedule": bool(cfg.get("auto_optimize_schedule", True)),
        "sync_horizon_days": int(cfg.get("sync_horizon_days", 14)),
        "ics_feed_token": cfg.get("ics_feed_token", ""),
        "last_sync_at": cfg.get("last_sync_at", ""),
        "last_sync_status": cfg.get("last_sync_status", ""),
        "last_sync_summary": cfg.get("last_sync_summary", {}),
        "last_error": cfg.get("last_error", ""),
        "cached_events_count": cached_count,
        "mapped_events_count": mapped_count,
        "overrides_count": overrides_count,
        "upcoming_external_events": upcoming_conflicts,
        "oauth_flow": oauth_flow_state,
    }


# ---------------------------------------------------------------------------
# OAuth 2.0 (PKCE Desktop Loopback & Web Callback) + API Requests
# ---------------------------------------------------------------------------

def _pkce_pair() -> Tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def build_oauth_authorize_url(redirect_uri: str, code_challenge: Optional[str] = None) -> Dict[str, str]:
    """Constructs Google OAuth2 authorization URL with PKCE + offline access."""
    cfg = get_gcalendar_config()
    if not cfg.get("client_id"):
        raise ValueError("Missing OAuth Client ID. Import Google OAuth credentials first.")

    verifier, auto_challenge = _pkce_pair()
    challenge = code_challenge or auto_challenge
    state = secrets.token_urlsafe(24)

    with _OAUTH_LOCK:
        _OAUTH_STATE_STORE[state] = {
            "code_verifier": verifier if code_challenge is None else "",
            "redirect_uri": redirect_uri,
            "created_at": time.time(),
        }
        # Prune states older than 15 minutes
        stale = [k for k, v in _OAUTH_STATE_STORE.items() if time.time() - v["created_at"] > 900]
        for k in stale:
            _OAUTH_STATE_STORE.pop(k, None)

    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": GCAL_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return {"auth_url": url, "state": state, "redirect_uri": redirect_uri}


def exchange_oauth_code(code: str, redirect_uri: str, state: str = "") -> Dict[str, Any]:
    """Exchanges authorization code for access + refresh tokens and saves them locally."""
    cfg = get_gcalendar_config()
    if not cfg.get("client_id"):
        raise ValueError("Missing OAuth Client ID.")

    code_verifier = ""
    if state:
        with _OAUTH_LOCK:
            meta = _OAUTH_STATE_STORE.pop(state, None)
            if meta:
                code_verifier = meta.get("code_verifier", "")

    form: Dict[str, str] = {
        "client_id": cfg["client_id"],
        "code": code.strip(),
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    if cfg.get("client_secret"):
        form["client_secret"] = cfg["client_secret"]
    if code_verifier:
        form["code_verifier"] = code_verifier

    status_code, body_text = _http_call("POST", GOOGLE_TOKEN_URL, form_data=form, timeout=20)
    if status_code >= 400:
        raise RuntimeError(f"OAuth token exchange failed ({status_code}): {body_text[:300]}")

    tok_data = json.loads(body_text or "{}")
    access_token = tok_data.get("access_token", "")
    refresh_token = tok_data.get("refresh_token") or cfg.get("refresh_token", "")
    expires_in = int(tok_data.get("expires_in", 3600))
    expires_at = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=expires_in)).isoformat()

    cfg["access_token"] = access_token
    if refresh_token:
        cfg["refresh_token"] = refresh_token
    cfg["token_expires_at"] = expires_at
    cfg["mode"] = "oauth"
    cfg["last_error"] = ""

    # Try resolving user email immediately
    if access_token:
        try:
            uinfo = _gcal_api_request("GET", GOOGLE_USERINFO_URL, access_token)
            if isinstance(uinfo, dict) and uinfo.get("email"):
                cfg["connected_email"] = uinfo["email"]
        except Exception:
            pass

    save_gcalendar_config(cfg)
    return get_gcalendar_status()


def start_desktop_oauth_flow(timeout_sec: int = 180) -> Dict[str, Any]:
    """
    Starts a temporary localhost loopback callback server (127.0.0.1:0) with PKCE,
    opens the system browser for Google OAuth consent, and completes exchange asynchronously.
    """
    cfg = get_gcalendar_config()
    if not cfg.get("client_id"):
        return {"started": False, "error": "Import or paste Google OAuth Client ID first."}

    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(24)

    class _CallbackHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/oauth2callback":
                self.send_response(404)
                self.end_headers()
                return
            qs = urllib.parse.parse_qs(parsed.query)
            got_state = (qs.get("state") or [""])[0]
            got_code = (qs.get("code") or [""])[0]
            got_err = (qs.get("error") or [""])[0]

            if got_err:
                html = f"<html><body style='font-family:sans-serif;background:#0f1116;color:#f3f4f6;padding:40px;'><h2>Google Authorization Cancelled</h2><p>{got_err}</p></body></html>"
                self._write_html(400, html)
                with _OAUTH_LOCK:
                    _LOOPBACK_STATE.update({"active": False, "status": "error", "error": got_err})
                return

            if got_state != state or not got_code:
                self._write_html(400, "<html><body><h2>Invalid OAuth state or missing code.</h2></body></html>")
                with _OAUTH_LOCK:
                    _LOOPBACK_STATE.update({"active": False, "status": "error", "error": "OAuth state mismatch"})
                return

            try:
                with _OAUTH_LOCK:
                    _OAUTH_STATE_STORE[got_state] = {
                        "code_verifier": verifier,
                        "redirect_uri": redirect_uri,
                        "created_at": time.time(),
                    }
                exchange_oauth_code(got_code, redirect_uri, got_state)
                self._write_html(
                    200,
                    "<html><body style='font-family:sans-serif;background:#0f1116;color:#f3f4f6;padding:40px;'>"
                    "<h2 style='color:#10b981;'>Harness Connected to Google Calendar</h2>"
                    "<p>You can close this browser tab and return to Harness Executive OS.</p>"
                    "<script>setTimeout(()=>window.close(), 1500);</script></body></html>",
                )
                with _OAUTH_LOCK:
                    _LOOPBACK_STATE.update({"active": False, "status": "connected", "error": ""})
            except Exception as exc:
                self._write_html(500, f"<html><body><h2>Token Exchange Failed</h2><p>{exc}</p></body></html>")
                with _OAUTH_LOCK:
                    _LOOPBACK_STATE.update({"active": False, "status": "error", "error": str(exc)})

        def _write_html(self, status_code: int, body: str) -> None:
            raw = body.encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = http.server.HTTPServer(("127.0.0.1", 0), _CallbackHandler)
    server.timeout = 1.0
    port = server.server_port
    redirect_uri = f"http://127.0.0.1:{port}/oauth2callback"

    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": GCAL_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

    with _OAUTH_LOCK:
        _LOOPBACK_STATE.update({"active": True, "status": "waiting", "error": "", "auth_url": auth_url})

    def _serve() -> None:
        deadline = time.time() + max(30, timeout_sec)
        try:
            while time.time() < deadline:
                with _OAUTH_LOCK:
                    if not _LOOPBACK_STATE.get("active"):
                        break
                server.handle_request()
        finally:
            try:
                server.server_close()
            except Exception:
                pass
            with _OAUTH_LOCK:
                if _LOOPBACK_STATE.get("status") == "waiting":
                    _LOOPBACK_STATE.update({"active": False, "status": "timeout", "error": "OAuth timed out"})

    threading.Thread(target=_serve, daemon=True).start()
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    return {"started": True, "auth_url": auth_url, "redirect_uri": redirect_uri}


def _gcal_api_request(
    method: str,
    path: str,
    token: str,
    payload: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Low-level Google Calendar REST v3 request helper (monkeypatchable in tests)."""
    url = path if path.startswith("https://") else f"{GCAL_API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if payload is not None:
        headers["Content-Type"] = "application/json"

    status_code, body_text = _http_call(method.upper(), url, headers=headers, json_body=payload, params=params, timeout=20)
    if status_code == 204 or not body_text:
        if status_code >= 400:
            raise RuntimeError(f"Google Calendar API error ({status_code})")
        return {}
    if status_code >= 400:
        msg = body_text[:300]
        try:
            err_json = json.loads(body_text)
            msg = err_json.get("error", {}).get("message", msg)
        except Exception:
            pass
        raise RuntimeError(f"Google Calendar API error ({status_code}): {msg}")
    return json.loads(body_text)


def _ensure_valid_access_token(cfg: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Returns valid Bearer token, refreshing via refresh_token if expired."""
    token = (cfg.get("access_token") or "").strip()
    expires_at = (cfg.get("token_expires_at") or "").strip()
    if token and expires_at:
        try:
            exp_dt = dt.datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=dt.timezone.utc)
            if exp_dt > dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=60):
                return token, cfg
        except Exception:
            pass

    refresh_tok = (cfg.get("refresh_token") or "").strip()
    if not refresh_tok:
        if token:
            return token, cfg
        raise RuntimeError("Google Calendar OAuth is not authenticated. Reconnect Google account.")

    form = {
        "client_id": cfg.get("client_id", ""),
        "refresh_token": refresh_tok,
        "grant_type": "refresh_token",
    }
    if cfg.get("client_secret"):
        form["client_secret"] = cfg["client_secret"]

    status_code, body_text = _http_call("POST", GOOGLE_TOKEN_URL, form_data=form, timeout=20)
    if status_code >= 400:
        raise RuntimeError(f"Google token refresh failed ({status_code}). Reconnect OAuth.")
    tok_data = json.loads(body_text or "{}")
    new_access = tok_data.get("access_token", "")
    expires_in = int(tok_data.get("expires_in", 3600))
    cfg["access_token"] = new_access
    cfg["token_expires_at"] = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=expires_in)).isoformat()
    save_gcalendar_config(cfg)
    return new_access, cfg


def list_calendars() -> List[Dict[str, Any]]:
    """Lists user's Google Calendars via CalendarList API."""
    cfg = get_gcalendar_config()
    if cfg.get("mode") != "oauth":
        return []
    token, cfg = _ensure_valid_access_token(cfg)
    data = _gcal_api_request("GET", "/users/me/calendarList", token)
    items = data.get("items") or []
    return [
        {
            "id": c.get("id", ""),
            "summary": c.get("summary", c.get("id", "")),
            "primary": bool(c.get("primary")),
            "accessRole": c.get("accessRole", ""),
            "backgroundColor": c.get("backgroundColor", ""),
        }
        for c in items
    ]


# ---------------------------------------------------------------------------
# Harness Canonical Item Collection (Exams, Homework, Lessons, Routine Plan)
# ---------------------------------------------------------------------------

def _normalize_subject(name: str) -> str:
    """Normalizes Polish subject strings for fuzzy exam-to-lesson matching."""
    text = unicodedata.normalize("NFKD", str(name or "").lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"^(j\.|jezyk)\s+", "", text.strip())
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _find_matching_lesson_window(subject: str, exam_date: str) -> Tuple[str, str, Optional[str]]:
    """Matches an exam's subject against TM1 lessons on exam_date to pick exact bell window."""
    try:
        from app.services import school_service
        lessons = school_service.get_lessons_for_date(exam_date) or []
    except Exception:
        lessons = []

    target_norm = _normalize_subject(subject)
    if target_norm and lessons:
        target_tokens = set(target_norm.split())
        best_match = None
        for lesson in lessons:
            lesson_subj = _normalize_subject(lesson.get("subject", ""))
            if not lesson_subj:
                continue
            if target_norm in lesson_subj or lesson_subj in target_norm:
                best_match = lesson
                break
            lesson_tokens = set(lesson_subj.split())
            if target_tokens & lesson_tokens:
                best_match = lesson
                break

        if best_match and best_match.get("time"):
            parsed = parse_time_window(best_match["time"])
            if parsed:
                sh, sm = divmod(parsed[0], 60)
                eh, em = divmod(parsed[1], 60)
                room = best_match.get("room")
                loc = f"Technikum Mechatroniczne nr 1 (Sala {room})" if room else "Technikum Mechatroniczne nr 1"
                return f"{sh:02d}:{sm:02d}", f"{eh:02d}:{em:02d}", loc

    return "08:00", "08:45", "Technikum Mechatroniczne nr 1"


def _compute_item_hash(item: Dict[str, Any]) -> str:
    canonical = {
        "kind": item["harness_kind"],
        "summary": item["summary"],
        "description": item["description"],
        "location": item["location"],
        "date": item["date"],
        "start_time": item["start_time"],
        "end_time": item["end_time"],
    }
    encoded = json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:24]


def collect_harness_events(
    start_date: Optional[str] = None,
    days_ahead: Optional[int] = None,
    cfg: Optional[Dict[str, Any]] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Collects canonical Harness items (exams, homework, lessons, plan blocks) across horizon."""
    cfg = cfg or get_gcalendar_config()
    start_s = start_date or _today_warsaw_str()
    horizon = max(1, int(days_ahead if days_ahead is not None else cfg.get("sync_horizon_days", 14)))
    start_dt = dt.date.fromisoformat(start_s)
    end_dt = start_dt + dt.timedelta(days=horizon - 1)
    end_s = end_dt.isoformat()

    own_conn = conn is None
    if own_conn:
        conn = get_connection()

    items: List[Dict[str, Any]] = []
    try:
        from app.services import homework_service, school_service, today_service

        # Calendar export range is inclusive of start_s..end_s; query with (start_dt - 1 day)
        # so exams/homework scheduled on start_s still appear on that calendar day without pruning.
        range_before_s = (start_dt - dt.timedelta(days=1)).isoformat()

        # 1. Upcoming Exams
        if cfg.get("sync_exams", True):
            exams = homework_service.get_upcoming_exams(today_str=range_before_s, conn=conn) or []
            for ex in exams:
                ex_date = ex.get("exam_date", "")
                if not ex_date or ex_date < start_s or ex_date > end_s:
                    continue
                st, et, loc = _find_matching_lesson_window(ex.get("subject", ""), ex_date)
                desc_parts = [f"Subject: {ex.get('subject', '')}"]
                if ex.get("scope"):
                    desc_parts.append(f"Scope: {ex['scope']}")
                desc_parts.append("Synced from Harness Executive OS (Exam)")
                item = {
                    "harness_key": f"exam:{ex['id']}",
                    "harness_kind": "exam",
                    "summary": f"[Test] {ex.get('subject', '')} — {ex.get('title', '')}".strip(" —"),
                    "description": "\n".join(desc_parts),
                    "location": loc or "",
                    "date": ex_date,
                    "start_time": st,
                    "end_time": et,
                    "color_id": "11",  # Tomato
                    "reminders": [{"method": "popup", "minutes": 1440}, {"method": "popup", "minutes": 60}],
                }
                item["sync_hash"] = _compute_item_hash(item)
                items.append(item)

        # 2. Homework Deadlines
        if cfg.get("sync_homework", True):
            homeworks = homework_service.get_upcoming_homework(today_str=range_before_s, auto_prune=False, conn=conn) or []
            for hw in homeworks:
                due_d = hw.get("due_date", "")
                if not due_d or due_d < start_s or due_d > end_s:
                    continue
                desc = f"Subject: {hw.get('subject', '')}\n{hw.get('description', '')}".strip()
                item = {
                    "harness_key": f"homework:{hw['id']}",
                    "harness_kind": "homework",
                    "summary": f"[HW] {hw.get('subject', '')} — {hw.get('title', '')}".strip(" —"),
                    "description": f"{desc}\nSynced from Harness Executive OS (Homework)",
                    "location": "",
                    "date": due_d,
                    "start_time": "07:30",
                    "end_time": "08:00",
                    "color_id": "5",  # Banana
                    "reminders": [{"method": "popup", "minutes": 720}],
                }
                item["sync_hash"] = _compute_item_hash(item)
                items.append(item)

        # 3. Daily School Timetable + Adaptive Plan Blocks
        for day_offset in range(horizon):
            cur_date = (start_dt + dt.timedelta(days=day_offset)).isoformat()
            lessons: List[Dict[str, Any]] = []
            if cfg.get("sync_school_timetable", True):
                lessons = school_service.get_lessons_for_date(cur_date) or []
                seen_nrs: Dict[str, int] = {}
                for lesson in lessons:
                    win = parse_time_window(lesson.get("time", ""))
                    if not win:
                        continue
                    sh, sm = divmod(win[0], 60)
                    eh, em = divmod(win[1], 60)
                    nr = str(lesson.get("nr", "?"))
                    seen_nrs[nr] = seen_nrs.get(nr, 0) + 1
                    suffix = f"_{seen_nrs[nr]}" if seen_nrs[nr] > 1 else ""
                    room = lesson.get("room")
                    summary = lesson.get("subject", "Lesson")
                    if room:
                        summary = f"{summary} (s. {room})"
                    desc_lines = [f"Lesson #{nr}"]
                    if lesson.get("teacher"):
                        desc_lines.append(f"Teacher: {lesson['teacher']}")
                    item = {
                        "harness_key": f"lesson:{cur_date}:{nr}{suffix}",
                        "harness_kind": "lesson",
                        "summary": summary,
                        "description": "\n".join(desc_lines),
                        "location": f"Technikum Mechatroniczne nr 1 (Sala {room})" if room else "Technikum Mechatroniczne nr 1",
                        "date": cur_date,
                        "start_time": f"{sh:02d}:{sm:02d}",
                        "end_time": f"{eh:02d}:{em:02d}",
                        "color_id": "8",  # Graphite
                        "reminders": [],
                    }
                    item["sync_hash"] = _compute_item_hash(item)
                    items.append(item)

            if cfg.get("sync_plan_blocks", True):
                sched = today_service.get_schedule_for_date(cur_date, conn=conn) or {}
                has_lessons = len(lessons) > 0
                mode_label = (sched.get("active_mode") or {}).get("mode_id", "NORMAL")
                color_by_type = {
                    "deep_work": "9",     # Blueberry
                    "study_block": "3",   # Grape
                    "training": "10",     # Basil
                    "german_code": "2",   # Sage
                    "school": "1",        # Lavender
                }
                for idx, blk in enumerate(sched.get("blocks", [])):
                    btype = blk.get("type", "")
                    if btype in ("sleep", "rest") and not cfg.get("include_sleep_rest_blocks", False):
                        continue
                    if btype == "school" and has_lessons and cfg.get("sync_school_timetable", True):
                        continue
                    if blk.get("gcal_user_deleted"):
                        continue
                    win = parse_time_window(blk.get("time", ""))
                    if not win:
                        continue
                    sh, sm = divmod(win[0], 60)
                    eh, em = divmod(win[1], 60)
                    desc_parts = [f"Mode: {mode_label}"]
                    activity_txt = blk.get("activity") or blk.get("description") or ""
                    if activity_txt:
                        desc_parts.append(activity_txt)
                    if blk.get("gcal_optimized") and blk.get("gcal_adjustment_reason"):
                        desc_parts.append(f"[Calendar Optimizer] {blk['gcal_adjustment_reason']}")
                    if blk.get("plan_phases"):
                        desc_parts.append("Phases:")
                        for p_idx, phase in enumerate(blk["plan_phases"], 1):
                            p_lbl = phase.get("label") or phase.get("title") or phase.get("name") or f"Phase {p_idx}"
                            desc_parts.append(f"{p_idx}. {p_lbl} ({phase.get('duration_min', 0)}m)")

                    item = {
                        "harness_key": f"plan:{cur_date}:{idx}",
                        "harness_kind": "plan_block",
                        "summary": blk.get("focus") or blk.get("label") or "Harness Block",
                        "description": "\n".join(desc_parts),
                        "location": blk.get("location", ""),
                        "date": cur_date,
                        "start_time": f"{sh:02d}:{sm:02d}",
                        "end_time": f"{eh:02d}:{em:02d}",
                        "color_id": color_by_type.get(btype, "7"),
                        "reminders": [{"method": "popup", "minutes": 10}] if btype in ("deep_work", "training") else [],
                    }
                    item["sync_hash"] = _compute_item_hash(item)
                    items.append(item)
    finally:
        if own_conn:
            conn.close()

    return items


# ---------------------------------------------------------------------------
# RFC 5545 .ics Feed Generation & Parsing
# ---------------------------------------------------------------------------

def _escape_ics_text(text: str) -> str:
    s = str(text or "")
    s = s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r\n", "\\n").replace("\n", "\\n")
    return s


def _unescape_ics_text(text: str) -> str:
    s = str(text or "")
    s = s.replace("\\n", "\n").replace("\\N", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")
    return s


def _fold_ics_line(line: str) -> str:
    if len(line) <= 74:
        return line
    chunks = [line[:74]]
    rest = line[74:]
    while rest:
        chunks.append(" " + rest[:73])
        rest = rest[73:]
    return "\r\n".join(chunks)


def generate_ics_feed(
    days_ahead: int = 14,
    start_date: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> str:
    """Generates a valid RFC 5545 .ics calendar subscription feed for Google Calendar."""
    cfg = get_gcalendar_config()
    items = collect_harness_events(start_date=start_date, days_ahead=days_ahead, cfg=cfg, conn=conn)
    now_utc = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Harness Executive OS//Calendar Cross-Sync//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Harness Executive OS",
        "X-WR-TIMEZONE:Europe/Warsaw",
        "BEGIN:VTIMEZONE",
        "TZID:Europe/Warsaw",
        "BEGIN:DAYLIGHT",
        "TZOFFSETFROM:+0100",
        "TZOFFSETTO:+0200",
        "TZNAME:CEST",
        "DTSTART:19700329T020000",
        "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU",
        "END:DAYLIGHT",
        "BEGIN:STANDARD",
        "TZOFFSETFROM:+0200",
        "TZOFFSETTO:+0100",
        "TZNAME:CET",
        "DTSTART:19701025T030000",
        "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU",
        "END:STANDARD",
        "END:VTIMEZONE",
    ]

    for item in items:
        d_compact = item["date"].replace("-", "")
        st_compact = item["start_time"].replace(":", "") + "00"
        et_compact = item["end_time"].replace(":", "") + "00"
        uid_safe = re.sub(r"[^A-Za-z0-9_.:-]", "-", item["harness_key"])

        lines.append("BEGIN:VEVENT")
        lines.append(_fold_ics_line(f"UID:{uid_safe}@harness.local"))
        lines.append(f"DTSTAMP:{now_utc}")
        lines.append(f"DTSTART;TZID=Europe/Warsaw:{d_compact}T{st_compact}")
        lines.append(f"DTEND;TZID=Europe/Warsaw:{d_compact}T{et_compact}")
        lines.append(_fold_ics_line(f"SUMMARY:{_escape_ics_text(item['summary'])}"))
        if item.get("description"):
            lines.append(_fold_ics_line(f"DESCRIPTION:{_escape_ics_text(item['description'])}"))
        if item.get("location"):
            lines.append(_fold_ics_line(f"LOCATION:{_escape_ics_text(item['location'])}"))
        lines.append("STATUS:CONFIRMED")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def _parse_ics_dt(raw_val: str, params: Dict[str, str]) -> Tuple[dt.datetime, bool]:
    """Parses ICS DTSTART/DTEND into local Europe/Warsaw naive datetime + is_all_day flag."""
    val = raw_val.strip()
    is_date_only = params.get("VALUE", "").upper() == "DATE" or (len(val) == 8 and val.isdigit())
    if is_date_only:
        d = dt.datetime.strptime(val[:8], "%Y%m%d")
        return d, True

    if val.endswith("Z"):
        utc_naive = dt.datetime.strptime(val[:-1][:15], "%Y%m%dT%H%M%S")
        return _convert_utc_to_warsaw(utc_naive), False

    tzid = params.get("TZID", "")
    naive = dt.datetime.strptime(val[:15], "%Y%m%dT%H%M%S")
    if tzid and tzid not in ("Europe/Warsaw", "Europe/Berlin", "CET", "CEST"):
        try:
            from zoneinfo import ZoneInfo
            utc_dt = naive.replace(tzinfo=ZoneInfo(tzid)).astimezone(dt.timezone.utc).replace(tzinfo=None)
            return _convert_utc_to_warsaw(utc_dt), False
        except Exception:
            pass
    return naive, False


def _parse_rrule_params(rrule_raw: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for part in rrule_raw.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip().upper()] = v.strip()
    return out


def _expand_rrule(
    base_start: dt.datetime,
    duration: dt.timedelta,
    rrule_raw: str,
    win_start: dt.date,
    win_end: dt.date,
) -> List[Tuple[dt.datetime, dt.datetime]]:
    """Safely expands common DAILY/WEEKLY/MONTHLY RRULE occurrences within [win_start, win_end]."""
    params = _parse_rrule_params(rrule_raw)
    freq = params.get("FREQ", "")
    if freq not in ("DAILY", "WEEKLY", "MONTHLY"):
        return [(base_start, base_start + duration)]

    try:
        interval = max(1, int(params.get("INTERVAL", "1")))
    except Exception:
        interval = 1

    try:
        max_count = min(200, int(params.get("COUNT", "200")))
    except Exception:
        max_count = 200

    until_dt: Optional[dt.datetime] = None
    if "UNTIL" in params:
        try:
            until_dt, _ = _parse_ics_dt(params["UNTIL"], {})
        except Exception:
            until_dt = None

    day_map = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}
    byday = [day_map[d[-2:]] for d in params.get("BYDAY", "").split(",") if d[-2:] in day_map]

    occurrences: List[Tuple[dt.datetime, dt.datetime]] = []
    cur = base_start
    count = 0
    step = 0
    while count < max_count and step < 500:
        step += 1
        if until_dt and cur > until_dt:
            break
        if cur.date() > win_end:
            break

        if freq == "WEEKLY" and byday:
            week_start = cur - dt.timedelta(days=cur.weekday())
            for wd in sorted(set(byday)):
                cand = dt.datetime.combine(week_start.date() + dt.timedelta(days=wd), cur.time())
                if cand < base_start:
                    continue
                if until_dt and cand > until_dt:
                    continue
                if count >= max_count:
                    break
                count += 1
                if cand.date() <= win_end and (cand + duration).date() >= win_start:
                    occurrences.append((cand, cand + duration))
            cur = cur + dt.timedelta(weeks=interval)
            continue

        count += 1
        if cur.date() <= win_end and (cur + duration).date() >= win_start:
            occurrences.append((cur, cur + duration))

        if freq == "DAILY":
            cur = cur + dt.timedelta(days=interval)
        elif freq == "WEEKLY":
            cur = cur + dt.timedelta(weeks=interval)
        else:  # MONTHLY
            month = cur.month - 1 + interval
            year = cur.year + month // 12
            month = month % 12 + 1
            day = min(cur.day, calendar.monthrange(year, month)[1])
            cur = cur.replace(year=year, month=month, day=day)

    return occurrences


def parse_ics_content(
    ics_text: str,
    start_date: str,
    end_date: str,
    calendar_id: str = "ical",
) -> List[Dict[str, Any]]:
    """Parses RFC 5545 text (UTC, TZID, all-day, RRULE) into normalized event dicts."""
    if not ics_text:
        return []
    unfolded = re.sub(r"\r?\n[ \t]", "", ics_text)
    raw_lines = re.split(r"\r?\n", unfolded)

    win_start = dt.date.fromisoformat(start_date[:10])
    win_end = dt.date.fromisoformat(end_date[:10])

    events: List[Dict[str, Any]] = []
    in_event = False
    props: Dict[str, Tuple[str, Dict[str, str]]] = {}

    for line in raw_lines:
        stripped = line.strip()
        if stripped == "BEGIN:VEVENT":
            in_event = True
            props = {}
            continue
        if stripped == "END:VEVENT" and in_event:
            in_event = False
            if "DTSTART" not in props:
                continue
            dt_start, is_all_day = _parse_ics_dt(props["DTSTART"][0], props["DTSTART"][1])
            if "DTEND" in props:
                dt_end, _ = _parse_ics_dt(props["DTEND"][0], props["DTEND"][1])
            else:
                dt_end = dt_start + (dt.timedelta(days=1) if is_all_day else dt.timedelta(minutes=60))
            duration = max(dt.timedelta(minutes=1), dt_end - dt_start)

            uid = _unescape_ics_text(props.get("UID", ("", {}))[0]) or secrets.token_hex(8)
            summary = _unescape_ics_text(props.get("SUMMARY", ("(No Title)", {}))[0])
            description = _unescape_ics_text(props.get("DESCRIPTION", ("", {}))[0])
            location = _unescape_ics_text(props.get("LOCATION", ("", {}))[0])
            status = (props.get("STATUS", ("confirmed", {}))[0] or "confirmed").lower()
            rrule = props.get("RRULE", ("", {}))[0]

            if rrule:
                instances = _expand_rrule(dt_start, duration, rrule, win_start, win_end)
            else:
                instances = [(dt_start, dt_end)]

            for idx, (inst_start, inst_end) in enumerate(instances):
                inst_date = inst_start.date()
                if is_all_day:
                    # DTEND is exclusive in RFC 5545 all-day events
                    last_day = (inst_end - dt.timedelta(days=1)).date()
                    if last_day < inst_date:
                        last_day = inst_date
                    if last_day < win_start or inst_date > win_end:
                        continue
                    cur_d = max(inst_date, win_start)
                    while cur_d <= min(last_day, win_end):
                        eid = uid if (not rrule and cur_d == inst_date) else f"{uid}__{cur_d.isoformat()}"
                        events.append({
                            "event_id": eid,
                            "calendar_id": calendar_id,
                            "summary": summary,
                            "description": description,
                            "location": location,
                            "date": cur_d.isoformat(),
                            "start_time": "",
                            "end_time": "",
                            "start_iso": cur_d.isoformat(),
                            "end_iso": (cur_d + dt.timedelta(days=1)).isoformat(),
                            "is_all_day": 1,
                            "status": status,
                            "is_harness_managed": 1 if uid.endswith("@harness.local") else 0,
                            "source": "ical",
                        })
                        cur_d += dt.timedelta(days=1)
                else:
                    if inst_date < win_start or inst_date > win_end:
                        continue
                    eid = uid if not rrule else f"{uid}__{inst_start.strftime('%Y%m%dT%H%M')}"
                    d_str = inst_date.isoformat()
                    st_str = inst_start.strftime("%H:%M")
                    et_str = inst_end.strftime("%H:%M")
                    events.append({
                        "event_id": eid,
                        "calendar_id": calendar_id,
                        "summary": summary,
                        "description": description,
                        "location": location,
                        "date": d_str,
                        "start_time": st_str,
                        "end_time": et_str,
                        "start_iso": format_local_iso(d_str, st_str),
                        "end_iso": format_local_iso(inst_end.date().isoformat(), et_str),
                        "is_all_day": 0,
                        "status": status,
                        "is_harness_managed": 1 if uid.endswith("@harness.local") else 0,
                        "source": "ical",
                    })
            continue

        if not in_event or ":" not in line:
            continue
        key_part, val_part = line.split(":", 1)
        segments = key_part.split(";")
        prop_name = segments[0].strip().upper()
        param_dict: Dict[str, str] = {}
        for seg in segments[1:]:
            if "=" in seg:
                pk, pv = seg.split("=", 1)
                param_dict[pk.strip().upper()] = pv.strip().strip('"')
        props[prop_name] = (val_part, param_dict)

    return events


def fetch_private_ical_feeds(
    urls: List[str],
    start_date: str,
    end_date: str,
) -> List[Dict[str, Any]]:
    """Downloads and parses validated public/private iCal feeds."""
    all_events: List[Dict[str, Any]] = []
    for idx, url in enumerate(urls):
        if not is_safe_calendar_url(url):
            raise ValueError(f"Blocked unsafe calendar URL: {_redact_ical_url(url)}")
        status_code, body_text = _http_call("GET", url, timeout=20)
        if status_code >= 400:
            raise RuntimeError(f"Failed to fetch iCal feed #{idx + 1} (HTTP {status_code})")
        cal_id = f"ical:{hashlib.sha256(url.encode('utf-8')).hexdigest()[:10]}"
        all_events.extend(parse_ics_content(body_text, start_date=start_date, end_date=end_date, calendar_id=cal_id))
    return all_events


# ---------------------------------------------------------------------------
# Tagged Test Import (Google Calendar -> `school_exams`)
# ---------------------------------------------------------------------------

def _extract_test_subject_and_title(summary: str) -> Optional[Tuple[str, str]]:
    m = TEST_TAG_PATTERN.match(summary or "")
    if not m:
        return None
    rest = m.group(1).strip()
    if not rest:
        return None
    for sep in (" — ", " - ", " – ", ": "):
        if sep in rest:
            subj, title = rest.split(sep, 1)
            return subj.strip() or "School", title.strip() or rest
    return "School", rest


def _import_tagged_events_to_exams(
    events: List[Dict[str, Any]],
    start_date: str,
    conn: sqlite3.Connection,
) -> int:
    """Imports external `[Test]` / `Sprawdzian` / `Kartkówka` events into `school_exams` idempotently."""
    from app.services import homework_service

    existing = conn.execute("SELECT subject, title, exam_date FROM school_exams").fetchall()
    seen_keys = {
        (_normalize_subject(row[0]), _normalize_subject(row[1]), str(row[2]))
        for row in existing
    }

    imported = 0
    for ev in events:
        if ev.get("is_harness_managed") or ev.get("status") == "cancelled":
            continue
        parsed = _extract_test_subject_and_title(ev.get("summary", ""))
        if not parsed:
            continue
        subj, title = parsed
        ex_date = ev.get("date", "")
        if not ex_date or ex_date < start_date:
            continue

        dedup_key = (_normalize_subject(subj), _normalize_subject(title), ex_date)
        if dedup_key in seen_keys:
            continue

        homework_service.add_exam(
            subject=subj,
            title=title,
            exam_date=ex_date,
            scope=(ev.get("description") or "").strip(),
            conn=conn,
        )
        seen_keys.add(dedup_key)
        imported += 1

    return imported


# ---------------------------------------------------------------------------
# Bidirectional Cross-Sync Engine (OAuth Pull -> DB Cache -> Push -> Cleanup)
# ---------------------------------------------------------------------------

def _normalize_gcal_api_event(raw: Dict[str, Any], calendar_id: str) -> Optional[Dict[str, Any]]:
    eid = raw.get("id")
    if not eid:
        return None
    status = raw.get("status", "confirmed")
    priv = (raw.get("extendedProperties") or {}).get("private") or {}
    is_harness = 1 if priv.get("harness_managed") == "true" else 0

    start_obj = raw.get("start") or {}
    end_obj = raw.get("end") or {}
    date_s = ""
    start_time = ""
    end_time = ""
    start_iso = ""
    end_iso = ""
    is_all_day = 0

    if "dateTime" in start_obj:
        date_s, start_time, start_iso = _parse_iso_datetime_to_warsaw(start_obj["dateTime"])
        if "dateTime" in end_obj:
            _, end_time, end_iso = _parse_iso_datetime_to_warsaw(end_obj["dateTime"])
        else:
            end_time = start_time
            end_iso = start_iso
    elif "date" in start_obj:
        date_s = start_obj["date"][:10]
        start_iso = date_s
        end_iso = (end_obj.get("date") or date_s)[:10]
        is_all_day = 1
    else:
        return None

    return {
        "event_id": eid,
        "calendar_id": calendar_id,
        "summary": raw.get("summary") or "(No Title)",
        "description": raw.get("description") or "",
        "location": raw.get("location") or "",
        "date": date_s,
        "start_time": start_time,
        "end_time": end_time,
        "start_iso": start_iso,
        "end_iso": end_iso,
        "is_all_day": is_all_day,
        "status": status,
        "is_harness_managed": is_harness,
        "harness_kind": priv.get("harness_kind", ""),
        "harness_key": priv.get("harness_key", ""),
        "pushed_date": priv.get("harness_pushed_date", ""),
        "pushed_start": priv.get("harness_pushed_start", ""),
        "pushed_end": priv.get("harness_pushed_end", ""),
        "etag": raw.get("etag") or "",
        "source": "gcal_api",
    }


def _upsert_cached_events(
    events: List[Dict[str, Any]],
    calendar_ids_pulled: List[str],
    start_date: str,
    end_date: str,
    conn: sqlite3.Connection,
) -> None:
    """Updates `gcal_events` for the pulled calendars in [start_date, end_date], pruning stale deletions."""
    ensure_gcal_tables(conn)
    for cal_id in calendar_ids_pulled:
        conn.execute(
            "DELETE FROM gcal_events WHERE calendar_id = ? AND date >= ? AND date <= ?",
            (cal_id, start_date, end_date),
        )

    for ev in events:
        if ev.get("status") == "cancelled":
            continue
        conn.execute(
            """
            INSERT OR REPLACE INTO gcal_events (
                event_id, calendar_id, summary, description, location,
                date, start_time, end_time, start_iso, end_iso, is_all_day,
                status, is_harness_managed, harness_kind, harness_key, etag, sync_hash, source, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                ev["event_id"],
                ev["calendar_id"],
                ev.get("summary", ""),
                ev.get("description", ""),
                ev.get("location", ""),
                ev["date"],
                ev.get("start_time", ""),
                ev.get("end_time", ""),
                ev.get("start_iso", ""),
                ev.get("end_iso", ""),
                int(ev.get("is_all_day", 0)),
                ev.get("status", "confirmed"),
                int(ev.get("is_harness_managed", 0)),
                ev.get("harness_kind", ""),
                ev.get("harness_key", ""),
                ev.get("etag", ""),
                ev.get("sync_hash", ""),
                ev.get("source", "gcal_api"),
            ),
        )


def _detect_user_overrides_from_remote(
    remote_harness_events: List[Dict[str, Any]],
    target_cal_id: str,
    conn: sqlite3.Connection,
) -> int:
    """Detects events dragged/resized/deleted by the user directly in Google Calendar UI."""
    overrides_found = 0
    seen_event_ids = set()
    for ev in remote_harness_events:
        seen_event_ids.add(ev["event_id"])
        h_key = ev.get("harness_key")
        if not h_key:
            continue
        if ev.get("status") == "cancelled":
            conn.execute(
                "UPDATE gcal_sync_map SET user_deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE harness_key = ?",
                (h_key,),
            )
            overrides_found += 1
            continue

        pushed_date = ev.get("pushed_date", "")
        pushed_start = ev.get("pushed_start", "")
        pushed_end = ev.get("pushed_end", "")
        if pushed_date and pushed_start and pushed_end:
            if (
                ev["date"] != pushed_date
                or ev["start_time"] != pushed_start
                or ev["end_time"] != pushed_end
            ):
                conn.execute(
                    """
                    UPDATE gcal_sync_map
                    SET override_date = ?, override_start = ?, override_end = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE harness_key = ?
                    """,
                    (ev["date"], ev["start_time"], ev["end_time"], h_key),
                )
                overrides_found += 1

    return overrides_found


def _ensure_target_calendar(cfg: Dict[str, Any], token: str) -> Tuple[str, Dict[str, Any]]:
    if not cfg.get("use_dedicated_calendar", True):
        return (cfg.get("target_calendar_id") or "primary"), cfg

    if cfg.get("target_calendar_id"):
        return cfg["target_calendar_id"], cfg

    desired_title = cfg.get("target_calendar_summary") or "Harness Executive OS"
    cals = _gcal_api_request("GET", "/users/me/calendarList", token).get("items") or []
    for c in cals:
        if (c.get("summary") or "").strip().lower() == desired_title.lower():
            cfg["target_calendar_id"] = c["id"]
            save_gcalendar_config(cfg)
            return c["id"], cfg

    created = _gcal_api_request(
        "POST",
        "/calendars",
        token,
        payload={
            "summary": desired_title,
            "description": "Synced exams, homework, school lessons & adaptive plan blocks from Harness Executive OS.",
            "timeZone": "Europe/Warsaw",
        },
    )
    cfg["target_calendar_id"] = created["id"]
    save_gcalendar_config(cfg)
    return created["id"], cfg


def _build_gcal_event_payload(item: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "summary": item["summary"],
        "description": item["description"],
        "location": item.get("location", ""),
        "start": {
            "dateTime": format_local_iso(item["date"], item["start_time"]),
            "timeZone": "Europe/Warsaw",
        },
        "end": {
            "dateTime": format_local_iso(item["date"], item["end_time"]),
            "timeZone": "Europe/Warsaw",
        },
        "colorId": item.get("color_id", "9"),
        "extendedProperties": {
            "private": {
                "harness_managed": "true",
                "harness_kind": item["harness_kind"],
                "harness_key": item["harness_key"],
                "harness_hash": item["sync_hash"],
                "harness_pushed_date": item["date"],
                "harness_pushed_start": item["start_time"],
                "harness_pushed_end": item["end_time"],
            }
        },
    }
    reminders = item.get("reminders")
    if reminders:
        payload["reminders"] = {"useDefault": False, "overrides": reminders}
    else:
        payload["reminders"] = {"useDefault": False, "overrides": []}
    return payload


def _should_cleanup_stale_mapping(
    row: sqlite3.Row,
    start_s: str,
    end_s: str,
    cfg: Dict[str, Any],
) -> bool:
    h_key = row["harness_key"]
    h_kind = row["harness_kind"]
    if row["user_deleted"]:
        return False
    if h_kind == "exam" and cfg.get("sync_exams", True):
        return True
    if h_kind == "homework" and cfg.get("sync_homework", True):
        return True
    if h_kind in ("plan_block", "lesson"):
        parts = h_key.split(":")
        if len(parts) >= 2 and start_s <= parts[1] <= end_s:
            if h_kind == "plan_block" and cfg.get("sync_plan_blocks", True):
                return True
            if h_kind == "lesson" and cfg.get("sync_school_timetable", True):
                return True
    return False


def get_cached_events(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Reads cached external Google Calendar / iCal events from SQLite."""
    start_s = start_date or _today_warsaw_str()
    end_s = end_date or (dt.date.fromisoformat(start_s) + dt.timedelta(days=13)).isoformat()
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        ensure_gcal_tables(conn)
        rows = conn.execute(
            """
            SELECT event_id, calendar_id, summary, description, location,
                   date, start_time, end_time, is_all_day, status, source
            FROM gcal_events
            WHERE date >= ? AND date <= ? AND status != 'cancelled' AND is_harness_managed = 0
            ORDER BY date ASC, start_time ASC
            """,
            (start_s, end_s),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if own_conn:
            conn.close()


def sync_all_gcalendar(
    start_date: Optional[str] = None,
    force_push: bool = False,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Executes full bidirectional Google Calendar cross-sync:
      1. Pull external events (OAuth Calendar v3 + any configured iCal feeds)
      2. Detect user edits/deletions to Harness events in Google Calendar
      3. Import tagged `[Test]` / `Sprawdzian` events into `school_exams`
      4. Collect schedule (now auto-optimized around newly pulled events)
      5. Push new/changed Harness events & clean up deleted ones idempotently
    """
    cfg = get_gcalendar_config()
    start_s = start_date or _today_warsaw_str()
    horizon = max(1, int(cfg.get("sync_horizon_days", 14)))
    end_dt = dt.date.fromisoformat(start_s) + dt.timedelta(days=horizon - 1)
    end_s = end_dt.isoformat()

    if cfg.get("mode") == "unconfigured" and not cfg.get("private_ical_urls"):
        return {"status": "unconfigured", "pulled_events": 0, "pushed_created": 0, "pushed_updated": 0, "pushed_deleted": 0, "imported_tests": 0}

    own_conn = conn is None
    if own_conn:
        conn = get_connection()

    pulled_events_all: List[Dict[str, Any]] = []
    pulled_cal_ids: List[str] = []
    imported_tests = 0
    pushed_created = 0
    pushed_updated = 0
    pushed_deleted = 0
    overrides_detected = 0

    try:
        ensure_gcal_tables(conn)

        # Pull configured private iCal feeds regardless of OAuth mode
        ical_urls = [u for u in cfg.get("private_ical_urls", []) if is_safe_calendar_url(u)]
        if ical_urls:
            ical_evts = fetch_private_ical_feeds(ical_urls, start_date=start_s, end_date=end_s)
            pulled_events_all.extend(ical_evts)
            for u in ical_urls:
                pulled_cal_ids.append(f"ical:{hashlib.sha256(u.encode('utf-8')).hexdigest()[:10]}")

        # OAuth 2-Way Sync
        if cfg.get("mode") == "oauth":
            token, cfg = _ensure_valid_access_token(cfg)
            if not cfg.get("connected_email"):
                try:
                    uinfo = _gcal_api_request("GET", GOOGLE_USERINFO_URL, token)
                    if isinstance(uinfo, dict) and uinfo.get("email"):
                        cfg["connected_email"] = uinfo["email"]
                        save_gcalendar_config(cfg)
                except Exception:
                    pass

            target_cal_id, cfg = _ensure_target_calendar(cfg, token)
            pull_ids = list(dict.fromkeys(list(cfg.get("pull_calendar_ids") or ["primary"]) + [target_cal_id]))

            time_min = format_local_iso(start_s, "00:00")
            time_max = format_local_iso((end_dt + dt.timedelta(days=1)).isoformat(), "00:00")

            remote_harness_events: List[Dict[str, Any]] = []
            for cal_id in pull_ids:
                cal_enc = urllib.parse.quote(cal_id, safe="")
                resp = _gcal_api_request(
                    "GET",
                    f"/calendars/{cal_enc}/events",
                    token,
                    params={
                        "timeMin": time_min,
                        "timeMax": time_max,
                        "singleEvents": "true",
                        "orderBy": "startTime",
                        "maxResults": 2500,
                    },
                )
                pulled_cal_ids.append(cal_id)
                for raw_ev in resp.get("items") or []:
                    norm = _normalize_gcal_api_event(raw_ev, cal_id)
                    if not norm:
                        continue
                    if norm["is_harness_managed"] and cal_id == target_cal_id:
                        remote_harness_events.append(norm)
                    else:
                        pulled_events_all.append(norm)

            overrides_detected = _detect_user_overrides_from_remote(remote_harness_events, target_cal_id, conn)
            _upsert_cached_events(pulled_events_all, pulled_cal_ids, start_s, end_s, conn)

            if cfg.get("import_tagged_tests", True):
                imported_tests = _import_tagged_events_to_exams(pulled_events_all, start_s, conn)
            conn.commit()

            # Collect schedule AFTER commit so conflict optimizer adapts to pulled events
            items = collect_harness_events(start_date=start_s, days_ahead=horizon, cfg=cfg, conn=conn)
            map_rows = {
                r["harness_key"]: r
                for r in conn.execute("SELECT * FROM gcal_sync_map").fetchall()
            }
            active_keys = set()
            target_enc = urllib.parse.quote(target_cal_id, safe="")

            for item in items:
                h_key = item["harness_key"]
                active_keys.add(h_key)
                mapped = map_rows.get(h_key)
                if mapped and mapped["user_deleted"]:
                    continue

                payload = _build_gcal_event_payload(item)
                if mapped and mapped["event_id"]:
                    if not force_push and mapped["sync_hash"] == item["sync_hash"]:
                        continue
                    eid_enc = urllib.parse.quote(mapped["event_id"], safe="")
                    try:
                        _gcal_api_request(
                            "PATCH",
                            f"/calendars/{target_enc}/events/{eid_enc}",
                            token,
                            payload=payload,
                        )
                        conn.execute(
                            "UPDATE gcal_sync_map SET sync_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE harness_key = ?",
                            (item["sync_hash"], h_key),
                        )
                        pushed_updated += 1
                    except Exception as exc:
                        if "(404)" in str(exc) or "(410)" in str(exc):
                            created = _gcal_api_request("POST", f"/calendars/{target_enc}/events", token, payload=payload)
                            conn.execute(
                                "UPDATE gcal_sync_map SET event_id = ?, sync_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE harness_key = ?",
                                (created["id"], item["sync_hash"], h_key),
                            )
                            pushed_created += 1
                        else:
                            raise
                else:
                    created = _gcal_api_request("POST", f"/calendars/{target_enc}/events", token, payload=payload)
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO gcal_sync_map (
                            harness_key, harness_kind, calendar_id, event_id, sync_hash, user_deleted, updated_at
                        ) VALUES (?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
                        """,
                        (h_key, item["harness_kind"], target_cal_id, created["id"], item["sync_hash"]),
                    )
                    pushed_created += 1

            # Clean up deleted/completed Harness items in Google Calendar
            for h_key, row in map_rows.items():
                if h_key in active_keys:
                    continue
                if not _should_cleanup_stale_mapping(row, start_s, end_s, cfg):
                    continue
                cal_enc = urllib.parse.quote(row["calendar_id"], safe="")
                eid_enc = urllib.parse.quote(row["event_id"], safe="")
                try:
                    _gcal_api_request("DELETE", f"/calendars/{cal_enc}/events/{eid_enc}", token)
                except Exception as exc:
                    if "(404)" not in str(exc) and "(410)" not in str(exc):
                        raise
                conn.execute("DELETE FROM gcal_sync_map WHERE harness_key = ?", (h_key,))
                pushed_deleted += 1

            conn.commit()
        else:
            # iCal-only mode: save pulled external events and optionally import tagged tests
            _upsert_cached_events(pulled_events_all, pulled_cal_ids, start_s, end_s, conn)
            if cfg.get("import_tagged_tests", True):
                imported_tests = _import_tagged_events_to_exams(pulled_events_all, start_s, conn)
            conn.commit()

        summary = {
            "status": "synced",
            "mode": cfg.get("mode"),
            "pulled_events": len(pulled_events_all),
            "imported_tests": imported_tests,
            "overrides_detected": overrides_detected,
            "pushed_created": pushed_created,
            "pushed_updated": pushed_updated,
            "pushed_deleted": pushed_deleted,
            "start_date": start_s,
            "end_date": end_s,
        }
        cfg["last_sync_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        cfg["last_sync_status"] = "synced"
        cfg["last_sync_summary"] = summary
        cfg["last_error"] = ""
        save_gcalendar_config(cfg)
        return summary
    except Exception as exc:
        cfg["last_sync_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        cfg["last_sync_status"] = "error"
        cfg["last_error"] = str(exc)
        save_gcalendar_config(cfg)
        raise
    finally:
        if own_conn:
            conn.close()
