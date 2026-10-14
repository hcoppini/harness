"""
Service for Daily Book Reading Tracker.
Maintains 1 book/month cadence with daily page-to-page targets and pace metrics.
"""

import sqlite3
from datetime import datetime, date
import calendar
from typing import Dict, Any, Optional
from app.db import get_connection


def ensure_book_tables(conn: sqlite3.Connection) -> None:
    """Ensures book tracking tables exist."""
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT DEFAULT '',
            total_pages INTEGER NOT NULL DEFAULT 300,
            current_page INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            month TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        );
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS reading_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER,
            date TEXT NOT NULL,
            start_page INTEGER NOT NULL,
            end_page INTEGER NOT NULL,
            pages_read INTEGER NOT NULL,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()


def get_active_book(date_str: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """Returns the currently active book, today's page target, and reading pace metrics."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    ensure_book_tables(conn)
    cursor = conn.cursor()

    target_date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    try:
        dt = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except Exception:
        dt = datetime.now().date()

    current_month_str = dt.strftime("%Y-%m")
    _, days_in_month = calendar.monthrange(dt.year, dt.month)
    days_left_in_month = max(1, days_in_month - dt.day + 1)

    cursor.execute(
        "SELECT * FROM books WHERE status = 'active' ORDER BY id DESC LIMIT 1"
    )
    book = cursor.fetchone()

    if not book:
        # Seed an initial book for Class 3 execution
        cursor.execute(
            """
            INSERT INTO books (title, author, total_pages, current_page, status, month)
            VALUES (?, ?, ?, ?, 'active', ?)
            """,
            ("Deep Work / Algorithmic Thinking", "Cal Newport", 300, 0, current_month_str),
        )
        conn.commit()
        cursor.execute("SELECT * FROM books WHERE status = 'active' ORDER BY id DESC LIMIT 1")
        book = cursor.fetchone()

    book_dict = dict(book)
    book_id = book_dict["id"]
    curr_page = int(book_dict["current_page"] or 0)
    total_pages = max(1, int(book_dict["total_pages"] or 300))

    # Fetch today's log
    cursor.execute(
        "SELECT * FROM reading_logs WHERE book_id = ? AND date = ? ORDER BY id DESC LIMIT 1",
        (book_id, target_date_str),
    )
    today_log = cursor.fetchone()

    pages_read_today = 0
    start_page_today = curr_page
    if today_log:
        pages_read_today = int(today_log["pages_read"])
        start_page_today = int(today_log["start_page"])

    pages_remaining = max(0, total_pages - curr_page)
    required_pace = round(pages_remaining / days_left_in_month, 1)
    daily_quota = max(15, min(35, round(total_pages / days_in_month)))
    target_page_today = min(total_pages, start_page_today + daily_quota)

    pct_done = round((curr_page / total_pages) * 100, 1)

    # Calculate reading streak
    cursor.execute(
        "SELECT DISTINCT date FROM reading_logs WHERE pages_read > 0 ORDER BY date DESC"
    )
    logged_dates = [r["date"] for r in cursor.fetchall()]
    streak = 0
    check_dt = dt
    if target_date_str not in logged_dates:
        # Check if completed yesterday
        check_dt = dt - calendar.datetime.timedelta(days=1)
    
    while check_dt.strftime("%Y-%m-%d") in logged_dates:
        streak += 1
        check_dt -= calendar.datetime.timedelta(days=1)

    if close_conn:
        conn.close()

    return {
        "book": book_dict,
        "date": target_date_str,
        "current_page": curr_page,
        "total_pages": total_pages,
        "pages_remaining": pages_remaining,
        "percent_completed": pct_done,
        "start_page_today": start_page_today,
        "target_page_today": target_page_today,
        "daily_quota": daily_quota,
        "pages_read_today": pages_read_today,
        "completed_today": pages_read_today >= daily_quota or (curr_page >= total_pages and curr_page > 0),
        "days_left_in_month": days_left_in_month,
        "required_daily_pace": required_pace,
        "reading_streak": streak,
    }


def log_reading_progress(
    end_page: int,
    start_page: Optional[int] = None,
    book_id: Optional[int] = None,
    notes: str = "",
    date_str: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Logs progress for today and updates current book page."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    ensure_book_tables(conn)
    cursor = conn.cursor()

    target_date = date_str or datetime.now().strftime("%Y-%m-%d")

    if not book_id:
        cursor.execute("SELECT id, current_page, total_pages FROM books WHERE status = 'active' ORDER BY id DESC LIMIT 1")
        b = cursor.fetchone()
        if not b:
            active_info = get_active_book(target_date, conn=conn)
            book_id = active_info["book"]["id"]
            cur_p = active_info["book"]["current_page"]
            tot_p = active_info["book"]["total_pages"]
        else:
            book_id = b["id"]
            cur_p = b["current_page"]
            tot_p = b["total_pages"]
    else:
        cursor.execute("SELECT current_page, total_pages FROM books WHERE id = ?", (book_id,))
        b = cursor.fetchone()
        cur_p = b["current_page"] if b else 0
        tot_p = b["total_pages"] if b else 300

    s_page = start_page if start_page is not None else cur_p
    e_page = max(s_page, int(end_page))
    pages_read = max(0, e_page - s_page)

    # Check existing log for today
    cursor.execute(
        "SELECT id FROM reading_logs WHERE book_id = ? AND date = ?",
        (book_id, target_date),
    )
    existing = cursor.fetchone()
    if existing:
        cursor.execute(
            """
            UPDATE reading_logs
            SET start_page = ?, end_page = ?, pages_read = ?, notes = ?
            WHERE id = ?
            """,
            (s_page, e_page, pages_read, notes, existing["id"]),
        )
    else:
        cursor.execute(
            """
            INSERT INTO reading_logs (book_id, date, start_page, end_page, pages_read, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (book_id, target_date, s_page, e_page, pages_read, notes),
        )

    # Update active book current_page
    new_status = "completed" if e_page >= tot_p else "active"
    comp_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if new_status == "completed" else None

    cursor.execute(
        """
        UPDATE books
        SET current_page = ?, status = ?, completed_at = ?
        WHERE id = ?
        """,
        (e_page, new_status, comp_at, book_id),
    )
    conn.commit()

    res = get_active_book(target_date, conn=conn)
    if close_conn:
        conn.close()
    return res


def update_book_details(
    book_id: int,
    title: str,
    author: str = "",
    total_pages: int = 300,
    current_page: int = 0,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Updates title, author, total pages or current position for a book."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    ensure_book_tables(conn)
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE books
        SET title = ?, author = ?, total_pages = ?, current_page = ?
        WHERE id = ?
        """,
        (title.strip(), author.strip(), int(total_pages), int(current_page), int(book_id)),
    )
    conn.commit()

    res = get_active_book(conn=conn)
    if close_conn:
        conn.close()
    return res
