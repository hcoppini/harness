"""
Service for AI-Powered Diary, Executive Coach, and Reflection System.
Supports 3 conversational stances (Coach, Friend, Objective Mirror) and
synthesizes raw thoughts into structured executive logs, action items, and habit entries.
"""

import os
import json
import sqlite3
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.db import get_connection


STANCE_PROMPTS = {
    "coach": (
        "You are the executive coach embedded in Harness OS for Heitor (16, Liceum Class 3 in Poland). "
        "His core ambitions: Direct admission to TUM Campus Heilbronn (B.Sc. Management & Data Science), "
        "scoring 90%+ on Rozszerzona Matura (Maths, CS), climbing German A2->B2, transitioning to competitive running, "
        "boxing 2x/week, and building to 80kg mass.\n"
        "YOUR ROLE AS COACH:\n"
        "- Hold a ruthless standard against intellectual excuses and drift.\n"
        "- In Class 3, only grades, tests, and graded projects count right now.\n"
        "- Be direct, concise, and tactical. Never use generic corporate fluff. Keep responses under 3-4 sentences.\n"
        "- Help Heitor bridge today's raw feelings into concrete immediate execution."
    ),
    "friend": (
        "You are Heitor's trusted friend and confidant in Harness OS. "
        "Heitor is a high-ambition 16-year-old balancing difficult Polish Liceum exams, TUM prep, running, and boxing.\n"
        "YOUR ROLE AS FRIEND:\n"
        "- Provide a non-judgmental, warm, grounding presence.\n"
        "- Listen deeply to frustrations, travel fatigue, academic setbacks, or stress.\n"
        "- Encourage him, remind him of his resilience, and help him decompress safely.\n"
        "- Keep responses concise (3-4 sentences), authentic, and human."
    ),
    "mirror": (
        "You are the Objective Mirror cognitive auditor in Harness OS for Heitor. "
        "YOUR ROLE AS OBJECTIVE MIRROR:\n"
        "- Strip away emotion, catastrophizing, and ego from whatever Heitor says.\n"
        "- Mirror back the bare, objective facts: What happened? What is within control? What is noise?\n"
        "- Highlight cognitive distortions (e.g. all-or-nothing thinking after a setback).\n"
        "- Keep responses crisp, structured, and completely objective (3-4 bullet points or short sentences)."
    ),
}


def ensure_diary_tables(conn: sqlite3.Connection) -> None:
    """Ensures diary conversation tables exist."""
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS diary_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            stance TEXT NOT NULL DEFAULT 'coach',
            messages_json TEXT DEFAULT '[]',
            structured_entry TEXT DEFAULT '',
            extracted_actions TEXT DEFAULT '[]',
            mood_score INTEGER DEFAULT 7,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()


def get_diary_conversation(date_str: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """Retrieves or initializes today's diary conversation."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    ensure_diary_tables(conn)
    cursor = conn.cursor()

    target_date = date_str or datetime.now().strftime("%Y-%m-%d")

    cursor.execute(
        "SELECT * FROM diary_conversations WHERE date = ? ORDER BY id DESC LIMIT 1",
        (target_date,),
    )
    row = cursor.fetchone()

    if not row:
        cursor.execute(
            """
            INSERT INTO diary_conversations (date, stance, messages_json, structured_entry, extracted_actions)
            VALUES (?, 'coach', '[]', '', '[]')
            """,
            (target_date,),
        )
        conn.commit()
        cursor.execute("SELECT * FROM diary_conversations WHERE date = ? ORDER BY id DESC LIMIT 1", (target_date,))
        row = cursor.fetchone()

    data = dict(row)
    try:
        data["messages"] = json.loads(data["messages_json"] or "[]")
    except Exception:
        data["messages"] = []

    try:
        data["actions"] = json.loads(data["extracted_actions"] or "[]")
    except Exception:
        data["actions"] = []

    if close_conn:
        conn.close()

    return data


def send_diary_message(
    user_message: str,
    stance: str = "coach",
    date_str: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Appends a user message to today's diary conversation and generates
    the corresponding AI coach/friend/mirror response.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    ensure_diary_tables(conn)
    cursor = conn.cursor()

    target_date = date_str or datetime.now().strftime("%Y-%m-%d")
    current_conv = get_diary_conversation(target_date, conn=conn)

    messages = current_conv.get("messages", [])
    now_time = datetime.now().strftime("%H:%M")

    messages.append({
        "role": "user",
        "content": user_message.strip(),
        "timestamp": now_time,
    })

    # Generate reply via LLM API or smart offline heuristic
    ai_reply = _generate_ai_reply(messages, stance=stance)

    messages.append({
        "role": "assistant",
        "stance": stance,
        "content": ai_reply,
        "timestamp": datetime.now().strftime("%H:%M"),
    })

    cursor.execute(
        """
        UPDATE diary_conversations
        SET stance = ?, messages_json = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (stance, json.dumps(messages), current_conv["id"]),
    )
    conn.commit()

    updated = get_diary_conversation(target_date, conn=conn)
    if close_conn:
        conn.close()
    return updated


def synthesize_diary_session(
    date_str: Optional[str] = None,
    auto_push_tasks: bool = True,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Synthesizes the raw conversation into structured executive takeaways:
    - Writes structured markdown entry into daily_logs.reflection_worked
    - Extracts actionable tasks and inserts into tasks table
    - Detects reading progress if mentioned
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    ensure_diary_tables(conn)
    cursor = conn.cursor()

    target_date = date_str or datetime.now().strftime("%Y-%m-%d")
    conv = get_diary_conversation(target_date, conn=conn)
    messages = conv.get("messages", [])

    if not messages:
        if close_conn:
            conn.close()
        return {"status": "empty", "message": "No messages in conversation to synthesize."}

    user_texts = [m["content"] for m in messages if m.get("role") == "user"]
    combined_raw = "\n".join(user_texts)

    # Generate synthesis
    synthesis = _synthesize_text(combined_raw, messages)

    # Save to diary_conversations
    cursor.execute(
        """
        UPDATE diary_conversations
        SET structured_entry = ?, extracted_actions = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            synthesis["structured_markdown"],
            json.dumps(synthesis["actions"]),
            conv["id"],
        ),
    )

    # Also sync into daily_logs reflection_worked so it shows in the Evening Honesty Diary!
    cursor.execute(
        """
        INSERT INTO daily_logs (date, reflection_worked, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(date) DO UPDATE SET
            reflection_worked = excluded.reflection_worked,
            updated_at = CURRENT_TIMESTAMP
        """,
        (target_date, synthesis["structured_markdown"]),
    )

    # Auto-push extracted actions to tasks table
    created_task_count = 0
    if auto_push_tasks and synthesis.get("actions"):
        for act in synthesis["actions"]:
            cursor.execute(
                """
                INSERT INTO tasks (title, category, is_tum, completed, date)
                VALUES (?, ?, ?, 0, ?)
                """,
                (
                    act.get("title", "Extracted Task"),
                    act.get("category", "study"),
                    1 if act.get("is_tum") else 0,
                    target_date,
                ),
            )
            created_task_count += 1

    conn.commit()

    res = {
        "status": "success",
        "date": target_date,
        "structured_entry": synthesis["structured_markdown"],
        "actions_created": created_task_count,
        "actions": synthesis["actions"],
    }

    if close_conn:
        conn.close()
    return res


def _generate_ai_reply(messages: List[Dict[str, str]], stance: str = "coach") -> str:
    """Invokes LLM API if key is configured, or provides high-signal heuristic coaching."""
    gemini_key = os.environ.get("GEMINI_API_KEY")
    system_instruction = STANCE_PROMPTS.get(stance, STANCE_PROMPTS["coach"])

    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            contents = []
            for m in messages[-8:]:
                contents.append({
                    "role": "user" if m.get("role") == "user" else "model",
                    "parts": [{"text": m.get("content", "")}],
                })

            payload = {
                "system_instruction": {"parts": [{"text": system_instruction}]},
                "contents": contents,
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 250},
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                return res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            pass

    # High-signal structured offline responses
    last_msg = messages[-1]["content"] if messages else ""
    return _offline_stance_reply(last_msg, stance)


def _offline_stance_reply(msg: str, stance: str) -> str:
    """High-context offline conversational reflections for Heitor."""
    low = msg.lower()
    if stance == "coach":
        if "tired" in low or "exhaust" in low or "overwhelm" in low:
            return "Fatigue is data, not a moral failure. With the US trip ending Oct 18, protect your 8–10h sleep window tonight. What is the single highest-priority test or project that moves the needle tomorrow?"
        if "test" in low or "sprawdzian" in low or "grade" in low:
            return "Class 3 rule: nothing but grades and tests count right now. Keep your SGH Library blocks 100% focused on active recall. How many days until this exam, and do you have past papers ready?"
        if "run" in low or "running" in low:
            return "Remember the rule: 2 easy conversational runs this week. No all-out 5K time trials yet. Build the aerobic floor first without blowing up your school recovery."
        return "I hear the intention. Now let's strip out the noise: what is the direct next action you will execute in the next 60 minutes?"

    elif stance == "friend":
        if "stress" in low or "tired" in low:
            return "You've been carrying a massive academic and physical load, plus the travel timezone shift. Give yourself some credit—you're doing great. Take a breath, drink water, and let's take tonight one step at a time."
        return "That makes complete sense. Don't be too hard on yourself; consistency over months is what actually wins. I'm right here with you."

    else:  # mirror
        return (
            "Observation: You are processing competing demands between immediate school deadlines and long-term targets. "
            "Reality check: The 2-week gap can be closed systematically station by station. "
            "Actionable distinction: Focus strictly on tomorrow's scheduled blocks; ignore everything outside the immediate 24-hour horizon."
        )


def _synthesize_text(raw_text: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Generates structured markdown summary and extracts tasks."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Extract bullet points from user thoughts
    raw_lines = [l.strip() for l in raw_text.split("\n") if len(l.strip()) > 3]
    points = raw_lines[:4] if raw_lines else ["Daily review completed."]

    summary_md = f"### Executive Diary Synthesis ({now_str})\n\n"
    summary_md += "**Core Reflections:**\n"
    for p in points:
        summary_md += f"- {p}\n"

    summary_md += "\n**Strategic Focus:**\n"
    summary_md += "- Academic Firewall: Class 3 tests & projects prioritized.\n"
    summary_md += "- Running/Athletic: 2x boxing + easy aerobic progression maintained.\n"

    # Basic action extraction
    actions = []
    for line in raw_lines:
        line_low = line.lower()
        if any(kw in line_low for kw in ["need to", "must", "have to", "prepare", "study", "code", "finish", "test"]):
            clean_title = line[:80].strip()
            actions.append({
                "title": clean_title,
                "category": "school" if any(w in line_low for w in ["test", "sprawdzian", "matura"]) else "study",
                "is_tum": 1 if any(w in line_low for w in ["math", "cs", "tum", "algorithm"]) else 0,
            })

    return {
        "structured_markdown": summary_md,
        "actions": actions[:5],
    }
