import streamlit as st
import re
from transcript import fetch_transcript, extract_video_id
from summarizer import summarize
from mindmap import render_mindmap, render_mindmap_fallback
from history import (init_db, save_summary, load_history,
                     load_summary_by_id, delete_summary,
                     clear_all_history, check_existing)
from utils import (render_highlighted_text, render_highlight_legend,
                   get_thumbnail_url, format_duration,
                   format_datetime, build_export_text, strip_highlight_tags)

# ─────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────

st.set_page_config(
    page_title="YT Summarizer",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────
# CSS
# ─────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700&family=DM+Sans:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.stApp {
    background: #080c14;
    color: #e2e8f0;
}

[data-testid="stSidebar"] {
    background: #0d1117;
    border-right: 1px solid #1e2d3d;
}

[data-testid="stSidebar"] * {
    font-family: 'DM Sans', sans-serif !important;
}

/* Input */
.stTextInput > div > div > input {
    background: #0d1117 !important;
    color: #e2e8f0 !important;
    border: 1px solid #1e2d3d !important;
    border-radius: 12px !important;
    padding: 14px 18px !important;
    font-size: 15px !important;
    font-family: 'DM Sans', sans-serif !important;
    transition: border-color 0.2s;
}
.stTextInput > div > div > input:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
}

/* Primary button */
.stButton > button {
    background: #3b82f6 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 12px 22px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    font-family: 'DM Sans', sans-serif !important;
    width: 100% !important;
    transition: background 0.2s, transform 0.1s !important;
    letter-spacing: 0.3px;
}
.stButton > button:hover {
    background: #2563eb !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active {
    transform: translateY(0px) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: #0d1117;
    border-radius: 12px;
    padding: 5px;
    gap: 4px;
    border: 1px solid #1e2d3d;
}
.stTabs [data-baseweb="tab"] {
    color: #64748b !important;
    font-weight: 500;
    font-family: 'DM Sans', sans-serif;
    border-radius: 8px !important;
    padding: 8px 16px !important;
    font-size: 14px !important;
}
.stTabs [aria-selected="true"] {
    background: #3b82f6 !important;
    color: #fff !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #1e2d3d; border-radius: 3px; }

/* Download button */
[data-testid="stDownloadButton"] button {
    background: #0d1117 !important;
    color: #3b82f6 !important;
    border: 1px solid #1e2d3d !important;
    border-radius: 10px !important;
    font-size: 13px !important;
    padding: 8px 16px !important;
    width: auto !important;
}

hr { border-color: #1e2d3d !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def card(content_fn, padding="24px"):
    st.markdown(f'<div style="background:#0d1117;border:1px solid #1e2d3d;border-radius:16px;padding:{padding};margin-bottom:16px;">', unsafe_allow_html=True)
    content_fn()
    st.markdown('</div>', unsafe_allow_html=True)

def section_label(icon, text):
    st.markdown(
        f'<p style="font-family:Syne,sans-serif;font-size:13px;font-weight:600;'
        f'color:#3b82f6;letter-spacing:1.5px;text-transform:uppercase;margin:0 0 14px;">'
        f'{icon} {text}</p>',
        unsafe_allow_html=True
    )

def show_highlighted(text):
    html = render_highlighted_text(text)
    st.markdown(
        f'<div style="font-size:15px;line-height:1.8;color:#cbd5e1;">{html}</div>',
        unsafe_allow_html=True
    )

def alert(text, kind="warning"):
    colors = {
        "warning": ("#f59e0b", "#1c1400", "#fcd34d"),
        "error":   ("#ef4444", "#1c0000", "#fca5a5"),
        "info":    ("#3b82f6", "#001840", "#93c5fd"),
    }
    border, bg, fg = colors.get(kind, colors["warning"])
    st.markdown(
        f'<div style="background:{bg};border-left:4px solid {border};'
        f'color:{fg};padding:12px 18px;border-radius:0 10px 10px 0;'
        f'margin:10px 0;font-size:14px;line-height:1.6;">{text}</div>',
        unsafe_allow_html=True
    )

# ─────────────────────────────────────────
# INIT
# ─────────────────────────────────────────

init_db()

for key, val in {
    "current_summary": None,
    "current_url": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<p style="font-family:Syne,sans-serif;font-size:20px;font-weight:700;'
        'color:#f1f5f9;margin:8px 0 4px;">🎬 YT Summarizer</p>'
        '<p style="font-size:12px;color:#475569;margin:0 0 20px;">Powered by Groq · LLaMA 3.3</p>',
        unsafe_allow_html=True
    )
    st.markdown('<hr style="margin:0 0 20px;">', unsafe_allow_html=True)

    st.markdown(
        '<p style="font-family:Syne,sans-serif;font-size:11px;font-weight:600;'
        'color:#3b82f6;letter-spacing:1.5px;text-transform:uppercase;margin:0 0 12px;">'
        '🕒 History</p>',
        unsafe_allow_html=True
    )

    history = load_history()

    if not history:
        st.markdown(
            '<p style="color:#475569;font-size:13px;padding:8px 0;">'
            'No summaries yet.<br>Paste a YouTube link to begin.</p>',
            unsafe_allow_html=True
        )
    else:
        if st.button("🗑 Clear All", key="clear_all"):
            clear_all_history()
            st.session_state.current_summary = None
            st.rerun()

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        for item in history:
            title = item['title'][:38] + ("…" if len(item['title']) > 38 else "")
            lang_badge = f"🌐 {item['language']}" if item['was_translated'] else f"🗣 {item['language']}"
            dur = format_duration(item['duration_minutes'])
            date = format_datetime(item['created_at'])

            col_btn, col_del = st.columns([6, 1])
            with col_btn:
                if st.button(f"📄 {title}", key=f"h_{item['id']}", help=f"{date} · {dur}"):
                    full = load_summary_by_id(item["id"])
                    st.session_state.current_summary = full
                    st.session_state.current_url = full.get("video_url", "")
                    st.rerun()
            with col_del:
                if st.button("✕", key=f"d_{item['id']}"):
                    delete_summary(item["id"])
                    if (st.session_state.current_summary and
                            st.session_state.current_summary.get("id") == item["id"]):
                        st.session_state.current_summary = None
                    st.rerun()

            st.markdown(
                f'<div style="margin:-6px 0 12px 2px;display:flex;gap:6px;flex-wrap:wrap;">'
                f'<span style="background:#1e2d3d;color:#64748b;font-size:11px;'
                f'padding:2px 8px;border-radius:20px;">{lang_badge}</span>'
                f'<span style="background:#1e2d3d;color:#64748b;font-size:11px;'
                f'padding:2px 8px;border-radius:20px;">⏱ {dur}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

# ─────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────

st.markdown(
    '<h1 style="font-family:Syne,sans-serif;font-size:32px;font-weight:700;'
    'color:#f1f5f9;margin:8px 0 4px;">YouTube Summarizer</h1>'
    '<p style="color:#475569;font-size:15px;margin:0 0 28px;">'
    'Paste any video link — get a full AI summary with highlights, key points & mind map.</p>',
    unsafe_allow_html=True
)

# ─────────────────────────────────────────
# URL INPUT
# ─────────────────────────────────────────

col_url, col_btn = st.columns([5, 1])
with col_url:
    url_input = st.text_input(
        "", placeholder="https://www.youtube.com/watch?v=...",
        label_visibility="collapsed", key="url_input"
    )
with col_btn:
    go = st.button("▶ Go", key="go_btn")

# ─────────────────────────────────────────
# SUMMARIZE
# ─────────────────────────────────────────

if go:
    if not url_input.strip():
        alert("⚠️ Please paste a YouTube URL first.", "warning")
    else:
        vid_id, vid_err = extract_video_id(url_input)
        if vid_err:
            alert(vid_err, "error")
        else:
            existing = check_existing(vid_id)
            if existing:
                alert(
                    f"📌 Already summarized on {format_datetime(existing['created_at'])}. Loading from history...",
                    "info"
                )
                full = load_summary_by_id(existing["id"])
                st.session_state.current_summary = full
                st.session_state.current_url = url_input
                st.rerun()
            else:
                with st.spinner("🔍 Fetching transcript..."):
                    tr = fetch_transcript(url_input)

                if "error" in tr:
                    alert(tr["error"], "error")
                else:
                    if tr.get("warning"):
                        alert(tr["warning"], "warning")
                    if not tr.get("is_english"):
                        alert(
                            f"🌐 Detected: <b>{tr['language_name']}</b> — translating to English...",
                            "info"
                        )

                    with st.spinner("🤖 Generating summary with Groq AI (LLaMA 3.3)..."):
                        sm = summarize(tr)

                    if "error" in sm:
                        alert(sm["error"], "error")
                    else:
                        new_id = save_summary(url_input, tr, sm)
                        sm["id"] = new_id
                        sm["video_url"] = url_input
                        sm["video_id"] = tr.get("video_id", "")
                        st.session_state.current_summary = sm
                        st.session_state.current_url = url_input
                        st.rerun()

# ─────────────────────────────────────────
# DISPLAY
# ─────────────────────────────────────────

if st.session_state.current_summary:
    sm = st.session_state.current_summary
    vid_id = sm.get("video_id", "")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Meta row ──
    c1, c2 = st.columns([1, 3])
    with c1:
        if vid_id:
            st.image(get_thumbnail_url(vid_id), use_container_width=True)

    with c2:
        lang = sm.get("original_language", "English")
        translated = sm.get("was_translated", False)
        dur = format_duration(sm.get("duration_minutes", 0))
        created = format_datetime(sm.get("created_at", ""))

        st.markdown(
            f'<p style="font-family:Syne,sans-serif;font-size:22px;font-weight:700;'
            f'color:#f1f5f9;margin:0 0 10px;">Summary Report</p>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px;">'
            f'<span style="background:#1e2d3d;color:#94a3b8;font-size:12px;padding:4px 12px;border-radius:20px;">'
            f'🌐 {lang}{" → English" if translated else ""}</span>'
            f'<span style="background:#1e2d3d;color:#94a3b8;font-size:12px;padding:4px 12px;border-radius:20px;">'
            f'⏱ {dur}</span>'
            f'<span style="background:#1e2d3d;color:#94a3b8;font-size:12px;padding:4px 12px;border-radius:20px;">'
            f'🕒 {created}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        export_text = build_export_text(sm)
        st.download_button(
            "⬇️ Download Summary (.txt)",
            data=export_text,
            file_name="yt_summary.txt",
            mime="text/plain"
        )

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    st.markdown("---")

    # # ── Highlight legend ──
    # render_highlight_legend()
    # st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Tabs ──
    t1, t2, t3, t4, t5 = st.tabs([
        "📝 Short Summary",
        "📖 Detailed Summary",
        "🔑 Key Points",
        "💡 Actionable Insights",
        "🗺️ Mind Map"
    ])

    # ── Tab 1: Short Summary ──
    with t1:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown(
            '<p style="font-family:Syne,sans-serif;font-size:13px;font-weight:600;'
            'color:#3b82f6;letter-spacing:1.5px;text-transform:uppercase;margin:0 0 14px;">'
            '📝 Short Summary</p>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div style="background:#0d1117;border:1px solid #1e2d3d;border-radius:16px;'
            f'padding:24px;">'
            f'<div style="font-size:16px;line-height:1.9;color:#cbd5e1;">'
            f'{render_highlighted_text(sm.get("short_summary",""))}'
            f'</div></div>',
            unsafe_allow_html=True
        )

    # ── Tab 2: Detailed Summary ──
    with t2:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown(
            '<p style="font-family:Syne,sans-serif;font-size:13px;font-weight:600;'
            'color:#3b82f6;letter-spacing:1.5px;text-transform:uppercase;margin:0 0 14px;">'
            '📖 Detailed Summary</p>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div style="background:#0d1117;border:1px solid #1e2d3d;border-radius:16px;'
            f'padding:24px;">'
            f'<div style="font-size:15px;line-height:1.9;color:#cbd5e1;">'
            f'{render_highlighted_text(sm.get("detailed_summary",""))}'
            f'</div></div>',
            unsafe_allow_html=True
        )

    # ── Tab 3: Key Points ──
    with t3:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown(
            '<p style="font-family:Syne,sans-serif;font-size:13px;font-weight:600;'
            'color:#3b82f6;letter-spacing:1.5px;text-transform:uppercase;margin:0 0 14px;">'
            '🔑 Key Points</p>',
            unsafe_allow_html=True
        )
        points_html = ""
        for point in sm.get("key_points", []):
            clean = render_highlighted_text(point)
            points_html += (
                f'<div style="display:flex;align-items:flex-start;gap:14px;'
                f'background:#0d1117;border:1px solid #1e2d3d;border-left:3px solid #3b82f6;'
                f'border-radius:0 12px 12px 0;padding:14px 18px;margin-bottom:10px;">'
                f'<span style="color:#3b82f6;font-weight:700;font-size:16px;margin-top:1px;flex-shrink:0;">•</span>'
                f'<span style="font-size:14px;line-height:1.8;color:#cbd5e1;">{clean}</span>'
                f'</div>'
            )
        st.markdown(points_html, unsafe_allow_html=True)

    # ── Tab 4: Actionable Insights ──
    with t4:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown(
            '<p style="font-family:Syne,sans-serif;font-size:13px;font-weight:600;'
            'color:#22c55e;letter-spacing:1.5px;text-transform:uppercase;margin:0 0 14px;">'
            '💡 Actionable Insights</p>',
            unsafe_allow_html=True
        )
        insights_html = ""
        for i, insight in enumerate(sm.get("actionable_insights", []), 1):
            clean = render_highlighted_text(insight)
            insights_html += (
                f'<div style="display:flex;align-items:flex-start;gap:14px;'
                f'background:#0d1117;border:1px solid #1e2d3d;border-left:3px solid #22c55e;'
                f'border-radius:0 12px 12px 0;padding:14px 18px;margin-bottom:10px;">'
                f'<span style="background:#22c55e;color:#000;font-weight:700;font-size:11px;'
                f'width:22px;height:22px;border-radius:50%;display:flex;align-items:center;'
                f'justify-content:center;flex-shrink:0;margin-top:2px;">{i}</span>'
                f'<span style="font-size:14px;line-height:1.8;color:#cbd5e1;">{clean}</span>'
                f'</div>'
            )
        st.markdown(insights_html, unsafe_allow_html=True)

    # ── Tab 5: Mind Map ──
    with t5:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown(
            '<p style="font-family:Syne,sans-serif;font-size:13px;font-weight:600;'
            'color:#3b82f6;letter-spacing:1.5px;text-transform:uppercase;margin:0 0 14px;">'
            '🗺️ Mind Map</p>',
            unsafe_allow_html=True
        )
        mmd = sm.get("mind_map_data", {})
        if mmd:
            try:
                success = render_mindmap(mmd)
                if not success:
                    raise Exception("render returned False")
            except Exception:
                fallback = render_mindmap_fallback(mmd)
                st.markdown(
                    f'<div style="background:#0d1117;border:1px solid #1e2d3d;'
                    f'border-radius:16px;padding:24px;">'
                    f'<pre style="color:#cbd5e1;font-size:14px;line-height:1.8;'
                    f'white-space:pre-wrap;margin:0;">{fallback}</pre></div>',
                    unsafe_allow_html=True
                )
        else:
            alert("Mind map data not available for this summary.", "info")

else:
    # ── Empty state ──
    st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div style="text-align:center;padding:40px 20px;">'
        '<div style="font-size:56px;margin-bottom:20px;">🎬</div>'
        '<p style="font-family:Syne,sans-serif;font-size:24px;font-weight:700;'
        'color:#1e2d3d;margin:0 0 10px;">Ready when you are</p>'
        '<p style="color:#475569;font-size:15px;margin:0;">'
        'Paste any YouTube URL above · Supports all languages · Saves history automatically'
        '</p></div>',
        unsafe_allow_html=True
    )