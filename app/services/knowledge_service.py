"""Service for Knowledge / Memory layer: first-principles algorithm notes, book insights, and reflections."""

import sqlite3
from typing import List, Dict, Any, Optional
from app.db import get_connection

SEED_KNOWLEDGE = [
    {
        "title": "First-Principles Protocol: Solving Coding Problems Without AI",
        "category": "algorithm",
        "tags": "matura, algorithms, independence, python",
        "content": (
            "### The 4-Step Independence Protocol\n\n"
            "1. **Plain-English Specification**: Read the problem statement twice. On paper or in this note, write down the input format, output format, and constraints (e.g. N <= 10^5 means O(N log N) or O(N)).\n"
            "2. **Manual Trace by Hand**: Take the sample input and solve it with pen and paper. Trace the variables at each step. If you cannot solve it on paper, you cannot code it.\n"
            "3. **Deconstruct the Core Algorithm**: Is it two pointers? Hash map lookup? Binary search? Dynamic programming? State the data structure and time complexity before typing one line.\n"
            "4. **Raw Code Implementation**: Open Python/C++ and write it without ChatGPT/Claude. If it errors or fails a test case, print debug variables yourself. Do not paste the prompt into AI."
        ),
    },
    {
        "title": "SIGG 24 Core Tactical Blueprint",
        "category": "mental_model",
        "tags": "sigg, gpw, finance, trading",
        "content": (
            "### Rules & Mechanics\n\n"
            "- **Stage 1 (Nov 17 - Jan 16)**: Capital 20k PLN. WIG20, mWIG40, sWIG80 + ETFs. Long only. Must trade in first 14 days.\n"
            "- **Stage 2 (Mar 2 - Mar 27)**: Capital 10k PLN. Futures contracts (FW20, FMW40, currencies, single stocks). Long and Short permitted.\n"
            "- **The 10-Second Rule**: No more than 1 order per 10s. Absolutely no automated execution bots.\n"
            "- **Educational Points**: Complete every video/quiz! Each point earned by the best team member adds +2 PLN to portfolio capital at end of Stage 1 (free riskless leverage)."
        ),
    },
    {
        "title": "TUM Heilbronn: Management & Data Science Criteria",
        "category": "mental_model",
        "tags": "tum, heilbronn, admission, matura",
        "content": (
            "### Strategic Focus\n\n"
            "- **Curriculum**: Intersection of Management, Machine Learning, Data Analytics, and Quantitative Finance.\n"
            "- **Abitur Equivalence**: High Polish Matura scores in Mathematics (Rozszerzona) and English.\n"
            "- **Differentiating Factor**: Concrete project ownership (Harness, SIGG trading engine, live apps) sets you apart from generic applicants."
        ),
    },
]


def seed_knowledge_if_empty(conn: sqlite3.Connection) -> None:
    """Seeds initial knowledge items if table is empty."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM knowledge_items")
    if cursor.fetchone()["cnt"] == 0:
        for item in SEED_KNOWLEDGE:
            cursor.execute(
                """
                INSERT INTO knowledge_items (title, category, tags, content)
                VALUES (?, ?, ?, ?)
                """,
                (item["title"], item["category"], item["tags"], item["content"]),
            )
        conn.commit()


def get_all_knowledge(category: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Returns all knowledge items, optionally filtered by category."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    seed_knowledge_if_empty(conn)
    cursor = conn.cursor()

    if category:
        cursor.execute(
            "SELECT * FROM knowledge_items WHERE category = ? ORDER BY updated_at DESC, id DESC",
            (category,),
        )
    else:
        cursor.execute("SELECT * FROM knowledge_items ORDER BY updated_at DESC, id DESC")

    rows = cursor.fetchall()
    items = [
        {
            "id": r["id"],
            "title": r["title"],
            "category": r["category"],
            "content": r["content"],
            "tags": r["tags"] or "",
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]

    if close_conn:
        conn.close()

    return items


def save_knowledge_item(
    title: str,
    category: str,
    content: str,
    tags: str = "",
    item_id: Optional[int] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Creates or updates a knowledge item."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    if item_id:
        cursor.execute(
            """
            UPDATE knowledge_items
            SET title = ?, category = ?, content = ?, tags = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (title.strip(), category.strip(), content.strip(), tags.strip(), item_id),
        )
        saved_id = item_id
    else:
        cursor.execute(
            """
            INSERT INTO knowledge_items (title, category, content, tags)
            VALUES (?, ?, ?, ?)
            """,
            (title.strip(), category.strip(), content.strip(), tags.strip()),
        )
        saved_id = cursor.lastrowid

    conn.commit()

    if close_conn:
        conn.close()

    return {
        "id": saved_id,
        "title": title,
        "category": category,
        "content": content,
        "tags": tags,
    }


def delete_knowledge_item(item_id: int, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Deletes a knowledge item."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute("DELETE FROM knowledge_items WHERE id = ?", (item_id,))
    conn.commit()
    deleted = cursor.rowcount > 0

    if close_conn:
        conn.close()

    return deleted
