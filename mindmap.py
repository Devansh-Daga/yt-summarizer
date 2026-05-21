from streamlit_agraph import agraph, Node, Edge, Config
import random

# ─────────────────────────────────────────
# COLOR SCHEME
# ─────────────────────────────────────────

CENTRAL_COLOR = "#6366f1"      # Indigo — central topic
BRANCH_COLORS = [
    "#f59e0b",                  # Amber
    "#10b981",                  # Emerald
    "#ef4444",                  # Red
    "#3b82f6",                  # Blue
    "#8b5cf6",                  # Purple
    "#ec4899",                  # Pink
]
SUBTOPIC_COLOR = "#1e293b"     # Dark slate
CENTRAL_FONT = "#ffffff"
BRANCH_FONT = "#ffffff"
SUBTOPIC_FONT = "#ffffff"


# ─────────────────────────────────────────
# MAIN MIND MAP RENDERER
# ─────────────────────────────────────────

def render_mindmap(mind_map_data: dict):
    """
    Takes mind_map_data dict from summarizer and renders
    an interactive mind map using streamlit-agraph.

    mind_map_data format:
    {
        "central_topic": "Main Topic",
        "branches": [
            {
                "topic": "Branch Name",
                "subtopics": ["sub1", "sub2"]
            },
            ...
        ]
    }
    """

    if not mind_map_data or not mind_map_data.get("central_topic"):
        return False

    nodes = []
    edges = []

    central_topic = mind_map_data.get("central_topic", "Main Topic")
    branches = mind_map_data.get("branches", [])

    # ── Central Node ──
    nodes.append(Node(
        id="central",
        label=wrap_label(central_topic, max_chars=20),
        size=40,
        color=CENTRAL_COLOR,
        font={"color": CENTRAL_FONT, "size": 18, "bold": True},
        shape="ellipse",
        title=central_topic
    ))

    # ── Branch Nodes ──
    for i, branch in enumerate(branches):
        branch_topic = branch.get("topic", f"Branch {i+1}")
        branch_id = f"branch_{i}"
        branch_color = BRANCH_COLORS[i % len(BRANCH_COLORS)]

        nodes.append(Node(
            id=branch_id,
            label=wrap_label(branch_topic, max_chars=18),
            size=28,
            color=branch_color,
            font={"color": BRANCH_FONT, "size": 14},
            shape="ellipse",
            title=branch_topic
        ))

        # Edge: central → branch
        edges.append(Edge(
            source="central",
            target=branch_id,
            color=branch_color,
            width=2.5,
        ))

        # ── Subtopic Nodes ──
        subtopics = branch.get("subtopics", [])
        for j, subtopic in enumerate(subtopics):
            subtopic_id = f"sub_{i}_{j}"

            nodes.append(Node(
                id=subtopic_id,
                label=wrap_label(subtopic, max_chars=20),
                size=18,
                color=SUBTOPIC_COLOR,
                font={"color": SUBTOPIC_FONT, "size": 12},
                shape="box",
                title=subtopic
            ))

            # Edge: branch → subtopic
            edges.append(Edge(
                source=branch_id,
                target=subtopic_id,
                color=branch_color,
                width=1.5,
                dashes=True
            ))

    # ── Graph Config ──
    config = Config(
        width="100%",
        height=580,
        directed=False,
        physics=True,
        hierarchical=False,
        nodeHighlightBehavior=True,
        highlightColor="#f0f0f0",
        collapsible=False,
        node={"labelProperty": "label"},
        link={"labelProperty": "label", "renderLabel": False},
        d3={
            "gravity": -300,
            "linkLength": 180,
            "linkStrength": 1,
            "alphaTarget": 0.05,
        }
    )

    # ── Render ──
    agraph(nodes=nodes, edges=edges, config=config)
    return True


# ─────────────────────────────────────────
# HELPER: LABEL WRAPPER
# ─────────────────────────────────────────

def wrap_label(text: str, max_chars: int = 20) -> str:
    """
    Wraps long labels into two lines for better readability in nodes.
    """
    if len(text) <= max_chars:
        return text

    words = text.split()
    lines = []
    current = ""

    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current = (current + " " + word).strip()
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return "\n".join(lines[:2])  # Max 2 lines per node


# ─────────────────────────────────────────
# FALLBACK: STATIC MIND MAP (if agraph fails)
# ─────────────────────────────────────────

def render_mindmap_fallback(mind_map_data: dict) -> str:
    """
    Returns a plain text mind map as fallback.
    Used if streamlit-agraph has rendering issues.
    """
    if not mind_map_data:
        return ""

    central = mind_map_data.get("central_topic", "Main Topic")
    branches = mind_map_data.get("branches", [])

    lines = [f"🎯 {central.upper()}"]
    lines.append("")

    for i, branch in enumerate(branches):
        branch_icons = ["🟡", "🟢", "🔴", "🔵", "🟣", "🟠"]
        icon = branch_icons[i % len(branch_icons)]
        lines.append(f"{icon} {branch.get('topic', '')}")

        for sub in branch.get("subtopics", []):
            lines.append(f"    ├── {sub}")

        lines.append("")

    return "\n".join(lines)