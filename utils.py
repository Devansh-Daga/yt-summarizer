import re
import streamlit as st
from datetime import datetime

# ─────────────────────────────────────────
# 1. HIGHLIGHT TAG RENDERER
# ─────────────────────────────────────────

# Color map for each tag type
HIGHLIGHT_STYLES = {
    "IMPORTANT": {
        "bg": "#fee2e2",        # Light red background
        "border": "#ef4444",    # Red border
        "text": "#991b1b",      # Dark red text
        "icon": "🔴",
        "label": "Important"
    },
    "CONCEPT": {
        "bg": "#dbeafe",        # Light blue background
        "border": "#3b82f6",    # Blue border
        "text": "#1e40af",      # Dark blue text
        "icon": "🔵",
        "label": "Concept"
    },
    "ACTION": {
        "bg": "#dcfce7",        # Light green background
        "border": "#22c55e",    # Green border
        "text": "#166534",      # Dark green text
        "icon": "🟢",
        "label": "Action"
    },
    "STAT": {
        "bg": "#fef9c3",        # Light yellow background
        "border": "#eab308",    # Yellow border
        "text": "#854d0e",      # Dark yellow text
        "icon": "🟡",
        "label": "Stat / Data"
    }
}


def render_highlighted_text(text: str) -> str:
    """
    Converts [TAG]...[/TAG] markers in text into
    styled HTML spans for Streamlit's st.markdown.

    Supports: [IMPORTANT], [CONCEPT], [ACTION], [STAT]
    """
    if not text:
        return ""

    for tag, style in HIGHLIGHT_STYLES.items():
        pattern = rf'\[{tag}\](.*?)\[/{tag}\]'
        replacement = (
            f'<span style="'
            f'background-color:{style["bg"]};'
            f'border-left: 4px solid {style["border"]};'
            f'color:{style["text"]};'
            f'padding: 2px 8px;'
            f'border-radius: 4px;'
            f'font-weight: 500;'
            f'display: inline;'
            f'">'
            f'{style["icon"]} \\1'
            f'</span>'
        )
        text = re.sub(pattern, replacement, text, flags=re.DOTALL)

    # Safety net: strip any leftover raw tags Groq didn't close properly
    text = re.sub(r'\[/?(?:IMPORTANT|CONCEPT|ACTION|STAT)\]', '', text)

    return text


def display_highlighted(text: str):
    """
    Renders highlighted text directly in Streamlit.
    Wraps render_highlighted_text and calls st.markdown.
    """
    html = render_highlighted_text(text)
    st.markdown(html, unsafe_allow_html=True)


# ─────────────────────────────────────────
# 2. HIGHLIGHT LEGEND
# ─────────────────────────────────────────

def render_highlight_legend():
    """
    Shows a small color legend explaining the highlight system.
    Display this near the top of the summary section.
    """
    st.markdown("**Color Legend:**", unsafe_allow_html=True)

    cols = st.columns(4)
    for i, (tag, style) in enumerate(HIGHLIGHT_STYLES.items()):
        with cols[i]:
            st.markdown(
                f'<div style="'
                f'background-color:{style["bg"]};'
                f'border-left: 4px solid {style["border"]};'
                f'color:{style["text"]};'
                f'padding: 6px 10px;'
                f'border-radius: 6px;'
                f'font-size: 13px;'
                f'font-weight:500;'
                f'text-align:center;'
                f'">{style["icon"]} {style["label"]}</div>',
                unsafe_allow_html=True
            )
    st.markdown("<br>", unsafe_allow_html=True)


# ─────────────────────────────────────────
# 3. THUMBNAIL FETCHER
# ─────────────────────────────────────────

def get_thumbnail_url(video_id: str) -> str:
    """
    Returns the YouTube thumbnail URL for a given video ID.
    Uses maxresdefault for best quality.
    """
    return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"


# ─────────────────────────────────────────
# 4. FORMAT DURATION
# ─────────────────────────────────────────

def format_duration(minutes: float) -> str:
    """
    Converts decimal minutes into a readable string.
    e.g. 75.5 → '1h 15m'
         12.3 → '12m'
    """
    if not minutes:
        return "Unknown duration"

    total_minutes = int(minutes)
    hours = total_minutes // 60
    mins = total_minutes % 60

    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{total_minutes}m"


# ─────────────────────────────────────────
# 5. FORMAT DATETIME
# ─────────────────────────────────────────

def format_datetime(dt_str: str) -> str:
    """
    Converts stored datetime string into a friendly format.
    e.g. '2024-01-15 14:32:00' → 'Jan 15, 2024 · 2:32 PM'
    """
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%b %d, %Y · %I:%M %p")
    except Exception:
        return dt_str


# ─────────────────────────────────────────
# 6. STRIP HIGHLIGHT TAGS (for plain text export)
# ─────────────────────────────────────────

def strip_highlight_tags(text: str) -> str:
    """
    Removes all highlight tags from text.
    Used when exporting summary as plain text.
    """
    return re.sub(r'\[/?(?:IMPORTANT|CONCEPT|ACTION|STAT)\]', '', text).strip()


# ─────────────────────────────────────────
# 7. EXPORT SUMMARY AS TEXT
# ─────────────────────────────────────────

def build_export_text(summary: dict) -> str:
    """
    Builds a clean plain-text version of the full summary
    for the download button.
    """
    lines = []

    lines.append("=" * 60)
    lines.append("YOUTUBE VIDEO SUMMARY")
    lines.append("=" * 60)
    lines.append(f"Video URL   : {summary.get('video_url', '')}")
    lines.append(f"Language    : {summary.get('original_language', 'English')}")
    lines.append(f"Duration    : {format_duration(summary.get('duration_minutes', 0))}")
    lines.append(f"Generated   : {format_datetime(summary.get('created_at', ''))}")
    lines.append("")

    lines.append("SHORT SUMMARY")
    lines.append("-" * 40)
    lines.append(strip_highlight_tags(summary.get("short_summary", "")))
    lines.append("")

    lines.append("DETAILED SUMMARY")
    lines.append("-" * 40)
    lines.append(strip_highlight_tags(summary.get("detailed_summary", "")))
    lines.append("")

    lines.append("KEY POINTS")
    lines.append("-" * 40)
    for i, point in enumerate(summary.get("key_points", []), 1):
        lines.append(f"{i}. {strip_highlight_tags(point)}")
    lines.append("")

    lines.append("ACTIONABLE INSIGHTS")
    lines.append("-" * 40)
    for i, insight in enumerate(summary.get("actionable_insights", []), 1):
        lines.append(f"{i}. {strip_highlight_tags(insight)}")
    lines.append("")

    lines.append("=" * 60)

    return "\n".join(lines)