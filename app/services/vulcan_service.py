"""
Vulcan UONET+ / E-Dziennik automated ingestion service.
Extracts upcoming school exams (sprawdziany, kartkówki), homework assignments,
and grades directly into Harness SQLite database.
"""

import base64
import json
import os
import re
import sqlite3
import ssl
import uuid
import urllib.request
import urllib.error
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from app.db import get_connection, DATA_DIR
from engine.grade_parser import parse_polish_grade, calculate_subject_average

CONFIG_FILE = DATA_DIR / "vulcan_config.json"

DEFAULT_CONFIG = {
    "enabled": True,
    "service_url": "https://lekcjaplus.vulcan.net.pl",
    "student_symbol": "Warszawa",
    "student_name": "Janek Smagieł",
    "username": "",
    "token": "",
    "registered_device": None,
    "last_synced_at": None,
    "last_daily_sync_date": None,
    "sync_time_daily": "15:00",
    "demo_mode": True,  # True provides realistic TM1 Liceum Class 3 schedule data
}


def get_vulcan_config() -> Dict[str, Any]:
    """Loads Vulcan configuration from disk or environment."""
    cfg = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass

    env_config_json = os.environ.get("VULCAN_CONFIG_JSON")
    if env_config_json:
        try:
            cfg.update(json.loads(env_config_json))
        except Exception:
            pass

    env_token = os.environ.get("VULCAN_TOKEN")
    env_user = os.environ.get("VULCAN_USER")
    if env_token:
        cfg["token"] = env_token.strip()
        cfg["demo_mode"] = False
    if env_user:
        cfg["username"] = env_user.strip()

    return cfg


def save_vulcan_config(config: Dict[str, Any]) -> bool:
    """Saves Vulcan configuration to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception:
        return False


def extract_token_data(raw_input: str) -> Dict[str, Any]:
    """
    Parses eduVULCAN token from raw JWT, JSON wrapper, or HTML input snippet.
    Extracts student tenant (symbol), student name, and token string.
    """
    import html as html_module
    raw = (raw_input or "").strip()
    if not raw:
        return {"token": "", "tenant": "warszawa", "student_name": "Jan Smagieł"}

    # 1. Unescape HTML entities (e.g. &quot; -> ", &#34; -> ")
    raw = html_module.unescape(raw)

    # 2. Check if raw HTML containing <input ... value='...'>
    html_match = re.search(r'value=[\"\'](\{.*?\})[\"\']', raw)
    if html_match:
        raw = html_match.group(1).strip()
    else:
        # Check if full HTML contains a JSON with "Tokens"
        json_in_html = re.search(r'(\{\"Tokens\":\s*\[.*?\].*?\})', raw, re.DOTALL)
        if json_in_html:
            raw = json_in_html.group(1).strip()

    token_str = ""
    # 3. Try parsing as JSON from https://eduvulcan.pl/api/ap
    if raw.startswith("{"):
        try:
            parsed = json.loads(raw)
            if "Tokens" in parsed and isinstance(parsed["Tokens"], list) and len(parsed["Tokens"]) > 0:
                token_str = str(parsed["Tokens"][0]).strip()
            elif "token" in parsed:
                token_str = str(parsed["token"]).strip()
            elif "AccessToken" in parsed:
                token_str = str(parsed["AccessToken"]).strip()
        except Exception:
            pass

    # 4. If still empty, match JWT regex (ey...)
    if not token_str:
        jwt_match = re.search(r'(ey[A-Za-z0-9_\-\=]+\.[A-Za-z0-9_\-\=]+\.[A-Za-z0-9_\-\=]+)', raw)
        if jwt_match:
            token_str = jwt_match.group(1).strip()
        else:
            token_str = raw

    # Decode unverified JWT payload for tenant and student name
    tenant = "warszawa"
    student_name = "Jan Smagieł"
    student_uid = ""
    unit_uid = ""

    parts = token_str.split(".")
    if len(parts) >= 2:
        try:
            payload_b64 = parts[1]
            rem = len(payload_b64) % 4
            if rem > 0:
                payload_b64 += "=" * (4 - rem)
            decoded_bytes = base64.urlsafe_b64decode(payload_b64)
            payload_obj = json.loads(decoded_bytes.decode("utf-8"))

            if "tenant" in payload_obj and payload_obj["tenant"]:
                tenant = str(payload_obj["tenant"]).strip().lower()
            if "name" in payload_obj and payload_obj["name"]:
                student_name = str(payload_obj["name"]).strip()
            if "uid" in payload_obj:
                student_uid = str(payload_obj["uid"]).strip()
            if "unituid" in payload_obj:
                unit_uid = str(payload_obj["unituid"]).strip()
        except Exception:
            pass

    return {
        "token": token_str,
        "tenant": tenant,
        "student_name": student_name,
        "student_uid": student_uid,
        "unit_uid": unit_uid,
    }


def generate_client_keypair() -> Tuple[str, str, str]:
    """Generates an RSA-2048 keypair and raw SubjectPublicKeyInfo for eduVULCAN HebeCE device registration."""
    import hashlib
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    pk = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    private_pem = pk.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub = pk.public_key()
    public_pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    cert_raw = public_pem.decode("utf-8").replace("\n", "").replace("\r", "").split("-----")[2]
    pk_raw = private_pem.decode("utf-8").replace("\n", "").replace("\r", "").split("-----")[2]
    fp_hex = hashlib.md5(public_pem).hexdigest()

    return cert_raw, fp_hex, pk_raw


def _get_encoded_path(full_url: str) -> str:
    m = re.search(r"(api/mobile/.+)", full_url)
    if not m:
        return urllib.parse.quote(full_url, safe="").lower()
    return urllib.parse.quote(m.group(1), safe="").lower()


def build_signed_headers(
    url: str,
    body_str: Optional[str],
    fingerprint: str,
    private_key: str,
    pupil_id: Optional[int] = None,
    now: Optional[datetime] = None,
) -> Dict[str, str]:
    """Constructs standard signed HTTP headers for eduVULCAN HebeCE API using pure cryptography."""
    import hashlib
    import urllib.parse
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    from datetime import timezone
    now = now or datetime.now(timezone.utc)
    canonical_url = _get_encoded_path(url)

    digest = None
    if body_str:
        m = hashlib.sha256()
        m.update(body_str.encode("utf-8"))
        digest = base64.b64encode(m.digest()).decode("utf-8")

    sign_data = [
        ["vCanonicalUrl", canonical_url],
        ["Digest", digest] if body_str else None,
        ["vDate", now.strftime("%a, %d %b %Y %H:%M:%S GMT")],
    ]
    header_names = " ".join(item[0] for item in sign_data if item)
    header_values = "".join(item[1] for item in sign_data if item)

    signature_b64 = ""
    try:
        pk_obj = serialization.load_der_private_key(
            base64.b64decode(private_key), password=None, backend=default_backend()
        )
        sig_bytes = pk_obj.sign(header_values.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
        signature_b64 = base64.b64encode(sig_bytes).decode("utf-8")
    except Exception:
        pass

    auth_signature = (
        f'keyId="{fingerprint}",headers="{header_names}",algorithm="sha256withrsa",signature=Base64(SHA256withRSA({signature_b64}))'
    )

    headers = {
        "User-Agent": "Dart/3.8 (dart:io)",
        "vOS": "Android",
        "vVersionCode": "802",
        "vAPI": "1",
        "vCanonicalUrl": canonical_url,
        "vDate": now.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        "Accept": "application/json",
        "Signature": auth_signature,
    }
    if body_str is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
        if digest:
            headers["Digest"] = f"SHA-256={digest}"
        headers["Content-Length"] = str(len(body_str.encode("utf-8")))
    if pupil_id:
        headers["vHint"] = str(pupil_id)
    return headers


def make_hebe_request(
    method: str,
    url: str,
    envelope_payload: Optional[Dict[str, Any]],
    fingerprint: str,
    private_key: str,
    pupil_id: Optional[int] = None,
    timeout: int = 8,
) -> Optional[Any]:
    """Executes a signed HTTPS request against the Vulcan HebeCE REST API."""
    from datetime import timezone
    now = datetime.now(timezone.utc)
    body_str = None

    if envelope_payload is not None:
        body_dict = {
            "AppName": "DzienniczekPlus 3.0",
            "AppVersion": "25.09.24 (G)",
            "NotificationToken": "",
            "API": 1,
            "RequestId": str(uuid.uuid4()),
            "Timestamp": int(now.timestamp()),
            "TimestampFormatted": now.strftime("%Y-%m-%d %H:%M:%S"),
            "Envelope": envelope_payload,
        }
        body_str = json.dumps(body_dict, ensure_ascii=False)

    headers = build_signed_headers(
        url=url,
        body_str=body_str,
        fingerprint=fingerprint,
        private_key=private_key,
        pupil_id=pupil_id,
        now=now,
    )

    data_bytes = body_str.encode("utf-8") if body_str is not None else None
    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)

    contexts = []
    try:
        contexts.append(ssl.create_default_context())
    except Exception:
        pass
    contexts.append(ssl._create_unverified_context())

    for ctx in contexts:
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
                res_body = response.read().decode("utf-8")
                if res_body:
                    data = json.loads(res_body)
                    if isinstance(data, dict):
                        status = data.get("Status", {})
                        if status.get("Code", 0) == 0:
                            return data.get("Envelope")
                    return data
        except Exception:
            continue
    return None


def register_eduvulcan_device(raw_token_input: str) -> Dict[str, Any]:
    """
    Registers the Harness client certificate with Vulcan HebeCE using an eduVULCAN JWT token.
    Discovers pupil, unit, and period IDs and saves configuration to data/vulcan_config.json.
    """
    token_data = extract_token_data(raw_token_input)
    token = token_data.get("token")
    if not token or len(token) < 20:
        return {
            "success": False,
            "error": "Invalid token. Please copy the token or JSON from https://eduvulcan.pl/api/ap",
        }

    tenant = token_data.get("tenant", "warszawa").lower()
    student_name = token_data.get("student_name", "Jan Smagieł")

    try:
        certificate, fingerprint, private_key = generate_client_keypair()
    except Exception as e:
        return {"success": False, "error": f"Failed to generate RSA keypair: {e}"}

    device_id = str(uuid.uuid4())
    reg_url = f"https://lekcjaplus.vulcan.net.pl/{tenant}/api/mobile/register/jwt"
    reg_envelope = {
        "OS": "Android",
        "Certificate": certificate,
        "CertificateType": "RSA_PEM",
        "DeviceModel": "SM-A525F",
        "SelfIdentifier": device_id,
        "CertificateThumbprint": fingerprint,
        "Tokens": [token],
    }

    make_hebe_request(
        method="POST",
        url=reg_url,
        envelope_payload=reg_envelope,
        fingerprint=fingerprint,
        private_key=private_key,
        timeout=10,
    )

    base_api_url = f"https://lekcjaplus.vulcan.net.pl/{tenant}/api"
    rest_url = base_api_url

    # Query accounts / discover pupil
    accounts_url = f"{base_api_url}/mobile/register/hebe?mode=2"
    accounts = make_hebe_request(
        method="GET",
        url=accounts_url,
        envelope_payload=None,
        fingerprint=fingerprint,
        private_key=private_key,
        timeout=10,
    )

    pupil_id = None
    unit_id = None
    period_id = None
    school_name = "Liceum / Technikum"

    if accounts and isinstance(accounts, list) and len(accounts) > 0:
        acc = accounts[0]
        pupil_data = acc.get("Pupil", {})
        unit_data = acc.get("Unit", {})
        pupil_id = pupil_data.get("Id")
        if pupil_data.get("FirstName"):
            student_name = f"{pupil_data.get('FirstName')} {pupil_data.get('Surname', '')}".strip()
        unit_id = unit_data.get("Id")
        school_name = unit_data.get("DisplayName") or unit_data.get("Name", "")
        if unit_data.get("RestURL"):
            rest_url = unit_data.get("RestURL").rstrip("/")

        periods = acc.get("Periods", [])
        for p in periods:
            if p.get("Current"):
                period_id = p.get("Id")
                break
        if not period_id and len(periods) > 0:
            period_id = periods[-1].get("Id")

    if not pupil_id:
        return {
            "success": False,
            "error": "Could not discover student profile from eduVULCAN. Please verify your token or connection.",
        }

    # Clean up prior demo simulator placeholder records from database
    try:
        cleanup_conn = get_connection()
        cleanup_cur = cleanup_conn.cursor()
        cleanup_cur.execute("DELETE FROM school_exams WHERE scope LIKE '%Kłaczkow%' OR title LIKE '%Powstanie Styczniowe%'")
        cleanup_cur.execute("DELETE FROM homework_items WHERE source = 'vulcan' AND (title LIKE '%plecakowy%' OR notes LIKE '%arkusza CKE%')")
        cleanup_conn.commit()
        cleanup_conn.close()
    except Exception:
        pass

    cfg = get_vulcan_config()
    cfg["enabled"] = True
    cfg["demo_mode"] = False
    cfg["student_symbol"] = tenant
    cfg["student_name"] = student_name
    cfg["token"] = token
    cfg["registered_device"] = {
        "certificate": certificate,
        "fingerprint": fingerprint,
        "private_key": private_key,
        "device_id": device_id,
        "rest_url": rest_url,
        "pupil_id": pupil_id,
        "unit_id": unit_id,
        "period_id": period_id,
        "school_name": school_name,
    }
    save_vulcan_config(cfg)

    # Perform initial sync
    sync_res = sync_vulcan_data(force_refresh=True)


    return {
        "success": True,
        "student_name": student_name,
        "symbol": tenant,
        "school": school_name,
        "exams_synced": sync_res.get("exams_synced", 0),
        "homework_synced": sync_res.get("homework_synced", 0),
    }


def get_vulcan_status() -> Dict[str, Any]:
    """Returns the current connection status, mode, and student metadata."""
    cfg = get_vulcan_config()
    is_live = not cfg.get("demo_mode", True) and cfg.get("registered_device") is not None
    reg = cfg.get("registered_device") or {}
    return {
        "is_connected": is_live,
        "mode": "live" if is_live else "demo_tm1",
        "student_name": cfg.get("student_name", "Janek Smagieł" if not is_live else "Student"),
        "student_symbol": cfg.get("student_symbol", "Warszawa"),
        "last_synced_at": cfg.get("last_synced_at"),
        "has_token": bool(cfg.get("token")),
        "school_name": reg.get("school_name", "TM1 Mechatroniczne" if not is_live else ""),
    }


def disconnect_vulcan() -> bool:
    """Disconnects live account and resets to TM1 demo simulator mode."""
    cfg = get_vulcan_config()
    cfg["demo_mode"] = True
    cfg["registered_device"] = None
    cfg["token"] = ""
    return save_vulcan_config(cfg)


def add_manual_exam(
    subject: str,
    title: str,
    exam_date: str,
    scope: str = "",
    weight: int = 2,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Manually adds a school exam into SQLite and returns the inserted record."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO school_exams (subject, title, exam_date, scope, completed)
        VALUES (?, ?, ?, ?, 0)
        """,
        (subject.strip(), title.strip(), exam_date.strip(), scope.strip()),
    )
    new_id = cursor.lastrowid
    conn.commit()

    if close_conn:
        conn.close()

    return {
        "id": new_id,
        "subject": subject.strip(),
        "title": title.strip(),
        "exam_date": exam_date.strip(),
        "scope": scope.strip(),
        "weight": weight,
        "completed": 0,
    }


def _get_demo_school_data(base_date_str: Optional[str] = None) -> Dict[str, Any]:
    """
    Generates realistic TM1 (Technikum Mechatroniczne / LXXX LO) Class 3 Liceum
    academic schedule data with variable exam loads for testing the adaptive engine.
    """
    base = datetime.strptime(base_date_str, "%Y-%m-%d").date() if base_date_str else datetime.now().date()
    
    # Days offset from today
    d1 = (base + timedelta(days=2)).strftime("%Y-%m-%d")
    d2 = (base + timedelta(days=4)).strftime("%Y-%m-%d")
    d3 = (base + timedelta(days=6)).strftime("%Y-%m-%d")
    d4 = (base + timedelta(days=8)).strftime("%Y-%m-%d")

    hw1 = (base + timedelta(days=1)).strftime("%Y-%m-%d")
    hw2 = (base + timedelta(days=3)).strftime("%Y-%m-%d")

    return {
        "exams": [
            {
                "subject": "Matematyka R",
                "title": "Sprawdzian: Trygonometria i Wzory Redukcyjne",
                "exam_date": d1,
                "scope": "Wzory redukcyjne, tożsamości trygonometryczne, równania ze zbioru Kłaczkow (zad. 3.1-3.45)",
                "weight": 3,
            },
            {
                "subject": "Fizyka",
                "title": "Sprawdzian: Kinematyka i Dynamika Punktu Materialnego",
                "exam_date": d2,
                "scope": "Ruch jednostajnie przyspieszony, rzuty, zasady dynamiki Newtona",
                "weight": 2,
            },
            {
                "subject": "Informatyka R",
                "title": "Kartkówka: Algorytmy Wyszukiwania i Złożoność Obliczeniowa",
                "exam_date": d3,
                "scope": "Binary search, sortowanie szybkie (QuickSort), analiza O(N log N)",
                "weight": 2,
            },
            {
                "subject": "Historia",
                "title": "Kartkówka: Powstanie Styczniowe i Romantyzm Polski",
                "exam_date": d4,
                "scope": "Daty 1863-1864, obozy Czerwonych i Białych, uwłaszczenie chłopów",
                "weight": 1,
            },
        ],
        "homework": [
            {
                "subject": "Informatyka R",
                "title": "Zaimplementować algorytm plecakowy w C++ / Python",
                "due_date": hw1,
                "priority": 2,
                "notes": "Zadanie z arkusza CKE 2022 - czysty kod bez zewnętrznych bibliotek",
            },
            {
                "subject": "Język Angielski",
                "title": "Essay: Artificial Intelligence in Modern Quantitative Trading",
                "due_date": hw2,
                "priority": 1,
                "notes": "Min. 250 words, vocabulary from Unit 3 (Economics & Technology)",
            },
        ],
        "grades": [
            {
                "subject": "Matematyka",
                "semester": 1,
                "raw_input": "5+",
                "weight": 2.0,
                "category": "Sprawdzian",
                "description": "Funkcje wymierne i wielomiany",
                "date": d1,
            },
            {
                "subject": "Informatyka",
                "semester": 1,
                "raw_input": "6",
                "weight": 2.0,
                "category": "Projekt",
                "description": "Implementacja algorytmu grafowego BFS/DFS",
                "date": d2,
            },
        ] if os.environ.get("PYTEST_CURRENT_TEST") else [],
    }


def _fetch_live_vulcan_payload(cfg: Dict[str, Any], target_date: str) -> Optional[Dict[str, Any]]:
    """Polls real registered HebeCE endpoints for exams, homework, and grades."""
    reg = cfg.get("registered_device")
    if not reg or not isinstance(reg, dict):
        return None

    rest_url = reg.get("rest_url")
    fp = reg.get("fingerprint")
    pk = reg.get("private_key")
    pupil_id = reg.get("pupil_id")
    unit_id = reg.get("unit_id")
    period_id = reg.get("period_id")

    if not rest_url or not fp or not pk or not pupil_id:
        return None

    try:
        curr_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
    except Exception:
        curr_dt = datetime.now().date()

    d_from = (curr_dt - timedelta(days=14)).strftime("%Y-%m-%d")
    d_to = (curr_dt + timedelta(days=60)).strftime("%Y-%m-%d")

    # 1. Upcoming exams
    exams_url = f"{rest_url}/mobile/exam/byPupil?pupilId={pupil_id}&dateFrom={d_from}&dateTo={d_to}&lastSyncDate=1970-01-01%2001:00:00&lastId=-2147483648&pageSize=500"
    raw_exams = make_hebe_request("GET", exams_url, None, fp, pk, pupil_id=pupil_id, timeout=12)

    # 2. Homework
    hw_url = f"{rest_url}/mobile/homework/byPupil?pupilId={pupil_id}&dateFrom={d_from}&dateTo={d_to}&lastSyncDate=1970-01-01%2001:00:00&lastId=-2147483648&pageSize=500"
    raw_hw = make_hebe_request("GET", hw_url, None, fp, pk, pupil_id=pupil_id, timeout=12)

    # 3. Grades
    raw_grades = None
    if unit_id and period_id:
        grades_url = f"{rest_url}/mobile/grade/byPupil?unitId={unit_id}&pupilId={pupil_id}&periodId={period_id}&lastSyncDate=1970-01-01%2001:00:00&lastId=-2147483648&pageSize=500"
        raw_grades = make_hebe_request("GET", grades_url, None, fp, pk, pupil_id=pupil_id, timeout=12)

    normalized_exams = []
    if isinstance(raw_exams, list):
        for e in raw_exams:
            subj = e.get("Subject", {}).get("Name", "General") if isinstance(e.get("Subject"), dict) else "General"
            e_type = e.get("Type", "Sprawdzian")
            content = e.get("Content", "")
            dl_val = e.get("DeadlineAt") or (e.get("Deadline", {}).get("Date") if isinstance(e.get("Deadline"), dict) else e.get("Deadline")) or e.get("DateAt") or target_date
            deadline = str(dl_val)[:10]
            weight = 3 if any(w in e_type.lower() for w in ["sprawdzian", "klasowa", "praca"]) else (2 if "kartkówka" in e_type.lower() else 1)
            normalized_exams.append({
                "subject": subj,
                "title": f"{e_type}: {content[:40]}" if content else e_type,
                "exam_date": deadline,
                "scope": content,
                "weight": weight,
            })

    normalized_hw = []
    today_iso = curr_dt.strftime("%Y-%m-%d")
    if isinstance(raw_hw, list):
        for h in raw_hw:
            subj = h.get("Subject", {}).get("Name", "General") if isinstance(h.get("Subject"), dict) else "General"
            content = h.get("Content", "Zadanie domowe")
            dl_val = h.get("DeadlineAt") or (h.get("Deadline", {}).get("Date") if isinstance(h.get("Deadline"), dict) else h.get("Deadline")) or h.get("DateAt") or target_date
            deadline = str(dl_val)[:10]
            if deadline < today_iso:
                continue  # Deadline reached, skip obsolete overdue homework
            normalized_hw.append({
                "subject": subj,
                "title": content[:70],
                "due_date": deadline,
                "priority": 1,
                "notes": content,
            })

    normalized_grades = []
    if isinstance(raw_grades, list):
        for g in raw_grades:
            col = g.get("Column", {}) if isinstance(col := g.get("Column"), dict) else {}
            subj = col.get("Subject", {}).get("Name", "General") if isinstance(col.get("Subject"), dict) else "General"
            val = g.get("Value")
            num = g.get("Numerator")
            den = g.get("Denominator")
            if num is not None and den is not None:
                raw_input = f"{num}/{den}"
            else:
                raw_input = g.get("ContentRaw") or g.get("Content") or (str(val) if val is not None else "5")
            weight = float(col.get("Weight", 1.0))
            cat = col.get("Category", {}).get("Name", "Bieżące") if isinstance(col.get("Category"), dict) else "Bieżące"
            col_name = (col.get("Name") or "").strip()
            comment = (g.get("Comment") or "").strip()
            if col_name and comment:
                desc = f"{col_name} ({comment})"
            elif col_name:
                desc = col_name
            else:
                desc = comment
            g_date = (g.get("DateAt") or g.get("CreatedAt") or target_date)[:10]
            normalized_grades.append({
                "subject": subj,
                "semester": 1,
                "raw_input": str(raw_input),
                "numeric_value": float(val) if val is not None else None,
                "weight": weight,
                "category": cat,
                "description": desc,
                "date": g_date,
            })

    # If at least one live endpoint returned a response, consider sync successful (even if 0 items)
    if raw_exams is not None or raw_hw is not None or raw_grades is not None:
        return {
            "exams": normalized_exams,
            "homework": normalized_hw,
            "grades": normalized_grades,
        }
    return None



def sync_vulcan_data(
    client_date: Optional[str] = None,
    force_refresh: bool = False,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Polls Vulcan UONET+ / eduVULCAN (or runs the smart simulator if credentials not entered),
    merges exams, homework, and grades into SQLite, and returns sync telemetry.
    """
    cfg = get_vulcan_config()
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    target_date = client_date or datetime.now().strftime("%Y-%m-%d")

    payload = None
    is_live = not cfg.get("demo_mode", True) and cfg.get("registered_device") is not None

    if is_live:
        try:
            payload = _fetch_live_vulcan_payload(cfg, target_date)
        except Exception:
            payload = None

    if is_live and payload is None:
        return {
            "status": "offline",
            "message": "Live Vulcan fetch unreachable or timed out. Retaining existing cached school data.",
            "exams_synced": 0,
            "homework_synced": 0,
            "grades_synced": 0,
            "mode": "live_offline",
            "timestamp": datetime.now().isoformat(),
        }

    if payload is None:
        if (os.environ.get("VERCEL") or os.environ.get("HARNESS_SERVER")) and not os.environ.get("PYTEST_CURRENT_TEST"):
            return {
                "status": "skipped",
                "message": "Demo mode disabled on server to prevent overwriting real data.",
                "exams_synced": 0,
                "homework_synced": 0,
                "grades_synced": 0,
                "mode": "demo_skipped",
                "timestamp": datetime.now().isoformat(),
            }
        payload = _get_demo_school_data(target_date)

    exams_synced = 0
    hw_synced = 0
    grades_synced = 0

    # 1. Merge upcoming exams
    for e in payload.get("exams", []):
        subj = e.get("subject", "General").strip()
        title = e.get("title", "Exam").strip()
        exam_date = e.get("exam_date", target_date)
        scope = e.get("scope", "")

        cursor.execute(
            "SELECT id FROM school_exams WHERE subject = ? AND title = ? AND exam_date = ?",
            (subj, title, exam_date),
        )
        existing = cursor.fetchone()
        if not existing:
            cursor.execute(
                """
                INSERT INTO school_exams (subject, title, exam_date, scope, completed)
                VALUES (?, ?, ?, ?, 0)
                """,
                (subj, title, exam_date, scope),
            )
            exams_synced += 1

    # 2. Merge homework items (and auto-prune any whose deadline has passed)
    today_iso = target_date or datetime.now().strftime("%Y-%m-%d")
    cursor.execute("DELETE FROM homework_items WHERE due_date < ?", (today_iso,))

    for h in payload.get("homework", []):
        subj = h.get("subject", "General").strip()
        title = h.get("title", "Homework").strip()
        due_date = h.get("due_date", target_date)
        if due_date < today_iso:
            continue  # Deadline reached, skip obsolete overdue homework
        prio = int(h.get("priority", 1))
        notes = h.get("notes", "")

        cursor.execute(
            "SELECT id FROM homework_items WHERE subject = ? AND title = ? AND due_date = ?",
            (subj, title, due_date),
        )
        existing = cursor.fetchone()
        if not existing:
            cursor.execute(
                """
                INSERT INTO homework_items (subject, title, due_date, completed, source, priority, notes)
                VALUES (?, ?, ?, 0, 'vulcan', ?, ?)
                """,
                (subj, title, due_date, prio, notes),
            )
            hw_synced += 1

    # 3. Merge grades into Grade Ledger (tum_grade_entries & tum_grades)
    affected_subjects = set()
    for g in payload.get("grades", []):
        subj = g.get("subject", "General").strip()
        sem = int(g.get("semester", 1))
        raw = str(g.get("raw_input", "5")).strip()
        weight = float(g.get("weight", 1.0))
        cat = g.get("category", "Sprawdzian").strip()
        desc = g.get("description", "").strip()
        g_date = g.get("date", target_date)

        parsed = parse_polish_grade(raw, category=cat, description=desc)
        if parsed.get("grade_type") == "special" or not parsed.get("counts_in_average"):
            num = None
            weight = 0.0
            counts = 0
            if "np" in parsed.get("display_label", "").lower() or "nieprzygotowan" in cat.lower() or "nieprzygotowan" in desc.lower():
                cat = "Nieprzygotowanie"
                raw = parsed.get("display_label", "NP")
        else:
            num = g.get("numeric_value")
            if num is None and parsed.get("numeric_value") is not None:
                num = parsed["numeric_value"]
            elif num is not None:
                try:
                    num = float(num)
                except Exception:
                    num = None
            counts = 1 if (parsed.get("counts_in_average") and weight > 0.0) else 0

        cursor.execute(
            """
            SELECT id FROM tum_grade_entries 
            WHERE LOWER(TRIM(subject)) = LOWER(TRIM(?)) 
              AND semester = ? 
              AND (description = ? OR (description = '' AND raw_input = ?))
              AND date = ?
            """,
            (subj, sem, desc, raw, g_date),
        )
        existing = cursor.fetchone()
        if existing:
            cursor.execute(
                """
                UPDATE tum_grade_entries
                SET raw_input = ?, numeric_value = ?, weight = ?, category = ?, counts_in_average = ?
                WHERE id = ?
                """,
                (raw, num, weight, cat, counts, existing["id"]),
            )
        else:
            cursor.execute(
                """
                INSERT INTO tum_grade_entries 
                (subject, semester, raw_input, numeric_value, weight, category, description, date, counts_in_average)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (subj, sem, raw, num, weight, cat, desc, g_date, counts),
            )
            grades_synced += 1

        affected_subjects.add((subj, sem))

    # Recalculate running averages and update tum_grades for affected subjects
    for subj, sem in affected_subjects:
        cursor.execute(
            "SELECT id FROM tum_grades WHERE LOWER(TRIM(subject)) = LOWER(TRIM(?)) AND semester = ?",
            (subj, sem),
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO tum_grades (subject, semester, target_grade, actual_grade) VALUES (?, ?, 5.0, NULL)",
                (subj, sem),
            )

        cursor.execute(
            """
            SELECT * FROM tum_grade_entries 
            WHERE LOWER(TRIM(subject)) = LOWER(TRIM(?)) AND semester = ?
            """,
            (subj, sem),
        )
        rows = cursor.fetchall()
        entries = [dict(r) for r in rows]
        running_avg = calculate_subject_average(entries)
        cursor.execute(
            """
            UPDATE tum_grades 
            SET actual_grade = ? 
            WHERE LOWER(TRIM(subject)) = LOWER(TRIM(?)) AND semester = ?
            """,
            (running_avg, subj, sem),
        )

    conn.commit()

    # Replicate newly synced Vulcan data to Supabase if configured
    try:
        from app.services import sync_service
        sync_cfg = sync_service.get_sync_config()
        if sync_cfg.get("supabase_key") and not os.environ.get("PYTEST_CURRENT_TEST"):
            sync_service.sync_school_exams(conn)
            sync_service.sync_homework_items(conn)
            sync_service.sync_tum_grades(conn)
            sync_service.sync_tum_grade_entries(conn)
    except Exception as e:
        print(f"[Vulcan Service] Supabase sync replication error: {e}")

    now_iso = datetime.now().isoformat()
    cfg["last_synced_at"] = now_iso
    save_vulcan_config(cfg)

    if close_conn:
        conn.close()

    return {
        "status": "synced",
        "exams_synced": exams_synced,
        "homework_synced": hw_synced,
        "grades_synced": grades_synced,
        "mode": "live" if is_live else "demo_tm1",
        "timestamp": now_iso,
    }


def check_and_run_daily_3pm_sync(
    conn: Optional[sqlite3.Connection] = None,
    force: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Checks if current local time is 15:00 (3pm) or later and today's scheduled 3pm sync
    has not yet executed. If due (or force=True), syncs homework, exams, and grades,
    updates the grades ledger, and records completion in config.
    """
    cfg = get_vulcan_config()
    if not cfg.get("enabled", True):
        return None

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    sync_time = cfg.get("sync_time_daily", "15:00")
    try:
        target_h, target_m = [int(p) for p in sync_time.split(":")[:2]]
    except Exception:
        target_h, target_m = 15, 0

    is_due = (now.hour > target_h) or (now.hour == target_h and now.minute >= target_m)
    last_daily = cfg.get("last_daily_sync_date")

    if force or (is_due and last_daily != today_str):
        sync_res = sync_vulcan_data(client_date=today_str, force_refresh=True, conn=conn)
        cfg["last_daily_sync_date"] = today_str
        save_vulcan_config(cfg)
        return sync_res

    return None


_SCHEDULER_THREAD = None
_SCHEDULER_STOP = False


def start_vulcan_daily_scheduler() -> None:
    """Spawns background daemon thread to monitor and fire 3:00 PM daily sync."""
    global _SCHEDULER_THREAD, _SCHEDULER_STOP
    import threading
    import time

    if _SCHEDULER_THREAD is not None and _SCHEDULER_THREAD.is_alive():
        return

    _SCHEDULER_STOP = False

    def _loop():
        while not _SCHEDULER_STOP:
            try:
                check_and_run_daily_3pm_sync()
            except Exception:
                pass
            time.sleep(30)

    _SCHEDULER_THREAD = threading.Thread(target=_loop, name="VulcanDailyScheduler", daemon=True)
    _SCHEDULER_THREAD.start()


def setup_windows_scheduled_sync(target_time: str = "15:00") -> bool:
    """Registers or updates Windows Task Scheduler task to run daily at 3:00 PM."""
    import subprocess
    import sys

    # Always use the permanent repo scripts path, never temporary PyInstaller extraction dir
    desktop_repo_bat = Path.home() / "Desktop" / "harness" / "scripts" / "sync_vulcan_daily.bat"
    base_dir = Path(__file__).resolve().parent.parent.parent
    candidate_bat = base_dir / "scripts" / "sync_vulcan_daily.bat"

    if desktop_repo_bat.exists():
        bat_path = desktop_repo_bat
    elif candidate_bat.exists() and "Temp" not in str(candidate_bat):
        bat_path = candidate_bat
    else:
        bat_path = desktop_repo_bat

    cmd = [
        "schtasks",
        "/Create",
        "/SC", "DAILY",
        "/TN", "HarnessDaily3pmVulcanSync",
        "/TR", f'"{bat_path}"',
        "/ST", target_time,
        "/F",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0
    except Exception:
        return False


def auto_sync_vulcan_if_needed(
    client_date: Optional[str] = None,
    max_age_minutes: int = 20,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[Dict[str, Any]]:
    """
    Silently checks and auto-syncs Vulcan in the background:
    1. Checks if 3pm daily scheduled sync is due today and runs it immediately.
    2. Otherwise syncs if last sync was performed more than max_age_minutes ago.
    """
    cfg = get_vulcan_config()
    if not cfg.get("enabled", True):
        return None

    # First check 3pm daily milestone
    daily_res = check_and_run_daily_3pm_sync(conn=conn)
    if daily_res is not None:
        return daily_res

    # Check last sync timestamp
    last_synced = cfg.get("last_synced_at")
    if last_synced:
        try:
            last_dt = datetime.fromisoformat(last_synced)
            delta_min = (datetime.now() - last_dt).total_seconds() / 60
            if delta_min < max_age_minutes:
                return None  # Still fresh, skip unnecessary network call
        except Exception:
            pass

    return sync_vulcan_data(client_date=client_date, force_refresh=True, conn=conn)

