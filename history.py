import sqlite3
import json
import os
from datetime import datetime
from transcript import fetch_video_title

DB_PATH = "history.db"

# ─────────────────────────────────────────
# 1. DATABASE SETUP
# ─────────────────────────────────────────

def init_db():
    """
    Creates the database and table if they don't exist.
    Call this once at app startup.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            video_url TEXT NOT NULL,
            video_title TEXT,
            duration_minutes REAL,
            original_language TEXT,
            was_translated INTEGER DEFAULT 0,
            short_summary TEXT,
            detailed_summary TEXT,
            key_points TEXT,
            actionable_insights TEXT,
            mind_map_data TEXT,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# ─────────────────────────────────────────
# 2. SAVE SUMMARY
# ─────────────────────────────────────────

def save_summary(video_url: str, transcript_result: dict, summary_result: dict) -> int:
    """
    Saves a completed summary to the database.
    Returns the new record's ID.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Generate a title from short summary (first 60 chars)
    # Use actual YouTube video title
    title = fetch_video_title(transcript_result.get("video_id", ""))
    if not title:
        # Fallback to short summary if title fetch fails
        import re
        short = summary_result.get("short_summary", "")
        clean_short = re.sub(r'\[/?(?:IMPORTANT|CONCEPT|ACTION|STAT)\]', '', short)
        title = clean_short[:60].strip() + ("..." if len(clean_short) > 60 else "")

    cursor.execute("""
        INSERT INTO summaries (
            video_id, video_url, video_title, duration_minutes,
            original_language, was_translated,
            short_summary, detailed_summary,
            key_points, actionable_insights, mind_map_data,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        transcript_result.get("video_id", ""),
        video_url,
        title,
        summary_result.get("duration_minutes", 0),
        summary_result.get("original_language", "English"),
        int(summary_result.get("was_translated", False)),
        summary_result.get("short_summary", ""),
        summary_result.get("detailed_summary", ""),
        json.dumps(summary_result.get("key_points", [])),
        json.dumps(summary_result.get("actionable_insights", [])),
        json.dumps(summary_result.get("mind_map_data", {})),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


# ─────────────────────────────────────────
# 3. LOAD ALL HISTORY (for sidebar)
# ─────────────────────────────────────────

def load_history() -> list:
    """
    Returns all summaries ordered by most recent first.
    Only returns lightweight fields for the sidebar list.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, video_title, video_url, original_language,
               was_translated, duration_minutes, created_at
        FROM summaries
        ORDER BY created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    history = []
    for row in rows:
        history.append({
            "id": row[0],
            "title": row[1] or "Untitled Summary",
            "url": row[2],
            "language": row[3],
            "was_translated": bool(row[4]),
            "duration_minutes": row[5],
            "created_at": row[6]
        })

    return history


# ─────────────────────────────────────────
# 4. LOAD SINGLE SUMMARY (when user clicks history item)
# ─────────────────────────────────────────

def load_summary_by_id(summary_id: int) -> dict:
    """
    Loads a full summary record by ID.
    Called when user clicks a history item.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM summaries WHERE id = ?
    """, (summary_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"error": "Summary not found."}

    return {
        "id": row[0],
        "video_id": row[1],
        "video_url": row[2],
        "video_title": row[3],
        "duration_minutes": row[4],
        "original_language": row[5],
        "was_translated": bool(row[6]),
        "short_summary": row[7],
        "detailed_summary": row[8],
        "key_points": json.loads(row[9] or "[]"),
        "actionable_insights": json.loads(row[10] or "[]"),
        "mind_map_data": json.loads(row[11] or "{}"),
        "created_at": row[12]
    }


# ─────────────────────────────────────────
# 5. DELETE A SUMMARY
# ─────────────────────────────────────────

def delete_summary(summary_id: int) -> bool:
    """
    Deletes a summary by ID.
    Returns True if successful.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM summaries WHERE id = ?", (summary_id,))
    affected = cursor.rowcount

    conn.commit()
    conn.close()

    return affected > 0


# ─────────────────────────────────────────
# 6. CHECK IF VIDEO ALREADY SUMMARIZED
# ─────────────────────────────────────────

def check_existing(video_id: str) -> dict | None:
    """
    Checks if a video was already summarized before.
    Returns the existing record or None.
    Helps avoid duplicate API calls.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, video_title, created_at
        FROM summaries
        WHERE video_id = ?
        ORDER BY created_at DESC
        LIMIT 1
    """, (video_id,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return {"id": row[0], "title": row[1], "created_at": row[2]}
    return None


# ─────────────────────────────────────────
# 7. CLEAR ALL HISTORY
# ─────────────────────────────────────────

def clear_all_history() -> bool:
    """
    Deletes all records. Used for a 'Clear History' button.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM summaries")
    conn.commit()
    conn.close()
    return True