"""
Trip Day-Planner — Streamlit UI
Design: Minimalist Monochrome (editorial luxury)
"""

import json
import streamlit as st
import streamlit.components.v1 as components
from pipeline import (
    stage1_understand, stage2_reason, stage3_produce, stage4_selfcheck,
    STAGE4_MAX_REDO,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Trip Planner",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Design system injection
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400;1,700&family=Source+Serif+4:ital,wght@0,300;0,400;0,600;1,300;1,400&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Reset & tokens ── */
:root {
    --bg: #FFFFFF;
    --fg: #000000;
    --muted: #F5F5F5;
    --muted-fg: #525252;
    --border: #000000;
    --border-light: #E5E5E5;
    --font-display: "Playfair Display", Georgia, serif;
    --font-body: "Source Serif 4", Georgia, serif;
    --font-mono: "JetBrains Mono", monospace;
}

/* ── Global ── */
html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg);
    font-family: var(--font-body);
    color: var(--fg);
}

/* Noise texture overlay */
[data-testid="stAppViewContainer"]::before {
    content: "";
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
    opacity: 0.018;
    pointer-events: none;
    z-index: 0;
}

[data-testid="stMain"] { background: transparent; }
[data-testid="stHeader"] { display: none; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stDecoration"] { display: none; }
.stMainBlockContainer { padding-top: 0 !important; max-width: 1100px; }

/* ── Typography ── */
h1, h2, h3, h4 {
    font-family: var(--font-display) !important;
    color: var(--fg);
    letter-spacing: -0.03em;
}

p, li, span { font-family: var(--font-body); }

/* ── Streamlit widget overrides ── */
/* Textarea */
[data-testid="stTextArea"] textarea {
    font-family: var(--font-body) !important;
    font-size: 1.05rem !important;
    background: var(--bg) !important;
    color: var(--fg) !important;
    border: none !important;
    border-bottom: 2px solid var(--border) !important;
    border-radius: 0 !important;
    padding: 1rem 0 !important;
    box-shadow: none !important;
    resize: none !important;
    line-height: 1.6 !important;
}
[data-testid="stTextArea"] textarea:focus {
    border-bottom: 4px solid var(--border) !important;
    outline: none !important;
}
[data-testid="stTextArea"] textarea::placeholder {
    color: var(--muted-fg);
    font-style: italic;
}
[data-testid="stTextArea"] label { display: none !important; }

/* Button */
[data-testid="stButton"] button,
[data-testid="stButton"] button p,
[data-testid="stButton"] button span {
    font-family: var(--font-mono) !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    background: var(--fg) !important;
    color: #ffffff !important;
    border: 2px solid var(--fg) !important;
    border-radius: 0 !important;
    padding: 0.9rem 2.5rem !important;
    transition: all 80ms !important;
    width: 100% !important;
}
[data-testid="stButton"] button:hover,
[data-testid="stButton"] button:hover p,
[data-testid="stButton"] button:hover span {
    background: #ffffff !important;
    color: #000000 !important;
}
[data-testid="stButton"] button:focus-visible {
    outline: 3px solid var(--fg) !important;
    outline-offset: 3px !important;
}

/* Status / expander containers */
[data-testid="stExpander"] {
    border: 1px solid var(--border-light) !important;
    border-radius: 0 !important;
    background: var(--bg) !important;
}
[data-testid="stExpander"] summary {
    font-family: var(--font-mono) !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}

/* Status widget */
[data-testid="stStatusWidget"] {
    border-radius: 0 !important;
    border: 1px solid var(--border-light) !important;
    font-family: var(--font-mono) !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--fg); }

/* ── Hide Streamlit heading anchor icons ── */
h1 a, h2 a, h3 a, h4 a,
.stMarkdown h1 a, .stMarkdown h2 a,
[data-testid="stMarkdownContainer"] a[href^="#"] {
    display: none !important;
}

/* ── Hide textarea label properly ── */
[data-testid="stTextArea"] label,
[data-testid="stTextArea"] > label,
[data-testid="stTextArea"] > div > label {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
    position: absolute !important;
}

/* ── Stronger font rendering ── */
* {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
}

/* ── Body text contrast ── */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {
    color: #000 !important;
}

/* Sidebar */
[data-testid="stSidebar"] { display: none; }

/* Alert / info boxes */
[data-testid="stAlert"] {
    border-radius: 0 !important;
    border-left: 4px solid var(--fg) !important;
    background: var(--muted) !important;
    font-family: var(--font-body) !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Helper: render components
# ---------------------------------------------------------------------------

def _mono(text: str) -> str:
    return f'<span style="font-family:var(--font-mono);font-size:0.72rem;letter-spacing:0.1em;text-transform:uppercase;color:var(--muted-fg)">{text}</span>'

def _rule(weight: int = 4) -> None:
    st.markdown(f'<hr style="border:none;border-top:{weight}px solid #000;margin:0"/>', unsafe_allow_html=True)

def _thin_rule() -> None:
    st.markdown('<hr style="border:none;border-top:1px solid #E5E5E5;margin:0.5rem 0"/>', unsafe_allow_html=True)

def render_hero() -> None:
    st.markdown("""
    <div style="padding: 5rem 0 3rem; position:relative;">
        <div style="
            position:absolute;inset:0;
            background-image: repeating-linear-gradient(0deg,transparent,transparent 1px,#000 1px,#000 2px);
            background-size: 100% 4px;
            opacity:0.012;pointer-events:none;
        "></div>
        <p style="
            font-family:var(--font-mono);font-size:0.72rem;
            letter-spacing:0.18em;text-transform:uppercase;
            color:var(--muted-fg);margin:0 0 1.5rem;
        ">&#10022; Prompt Pipeline &mdash; Trip Planner</p>
        <div style="
            font-family:'Playfair Display',Georgia,serif;
            font-size:clamp(3.5rem,9vw,8rem);
            font-weight:900;line-height:0.95;
            letter-spacing:-0.04em;margin:0 0 1.5rem;
            color:#000;
        ">Plan<br><em style='font-weight:400'>your</em><br>Journey&#46;</div>
        <div style="display:flex;align-items:center;gap:1rem;margin-top:2rem;">
            <div style="width:48px;height:4px;background:#000"></div>
            <div style="width:12px;height:12px;border:2px solid #000"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _scroll_to_bottom() -> None:
    """Scroll the page to the bottom after each stage completes."""
    components.html(
        "<script>window.parent.scrollTo({top: window.parent.document.body.scrollHeight, behavior: 'smooth'});</script>",
        height=0,
    )

def render_constraints(s1: dict) -> None:
    st.markdown(_mono("Parsed Constraints"), unsafe_allow_html=True)
    cols = st.columns(4)
    fields = [
        ("City", s1.get("city", "—")),
        ("Days", str(s1.get("days", "—"))),
        ("Budget", s1.get("budget_level", "—").upper()),
        ("Style", s1.get("travel_style", "—").upper()),
    ]
    for col, (label, val) in zip(cols, fields):
        with col:
            st.markdown(f"""
            <div style="border:1px solid #000;padding:1.2rem 1rem;background:var(--bg)">
                <div style="font-family:var(--font-mono);font-size:0.65rem;letter-spacing:0.12em;text-transform:uppercase;color:var(--muted-fg);margin-bottom:0.4rem">{label}</div>
                <div style="font-family:var(--font-display);font-size:1.5rem;font-weight:700;letter-spacing:-0.02em">{val}</div>
            </div>
            """, unsafe_allow_html=True)

    interests = s1.get("interests", [])
    dietary = s1.get("dietary_restrictions", [])
    mobility = s1.get("mobility_notes")

    tags_html = "".join(
        f'<span style="border:1px solid #000;padding:0.2rem 0.6rem;font-family:var(--font-mono);font-size:0.65rem;letter-spacing:0.08em;text-transform:uppercase;margin-right:0.4rem;margin-bottom:0.4rem;display:inline-block">{t}</span>'
        for t in interests
    )
    if tags_html:
        st.markdown(f'<div style="margin-top:1rem">{_mono("Interests")}<div style="margin-top:0.5rem">{tags_html}</div></div>', unsafe_allow_html=True)

    if dietary:
        st.markdown(f'<div style="margin-top:0.6rem">{_mono("Dietary")} &nbsp;<span style="font-family:var(--font-body);font-size:0.9rem">{", ".join(dietary)}</span></div>', unsafe_allow_html=True)
    if mobility:
        st.markdown(f'<div style="margin-top:0.4rem">{_mono("Mobility")} &nbsp;<span style="font-family:var(--font-body);font-size:0.9rem;font-style:italic">{mobility}</span></div>', unsafe_allow_html=True)

def render_reasoning(s2: dict) -> None:
    st.markdown(f"""
    <div style="
        background:var(--muted);border-left:4px solid #000;
        padding:1.5rem 1.5rem 1.5rem 2rem;margin:1rem 0;
        position:relative;
    ">
        <div style="position:absolute;top:-0.8rem;left:2rem;background:var(--muted);padding:0 0.4rem;font-family:var(--font-display);font-size:2.5rem;font-weight:900;font-style:italic;line-height:1">"</div>
        <p style="font-family:var(--font-body);font-size:0.95rem;line-height:1.7;color:#333;margin:0.5rem 0 0">{s2.get("reasoning","")}</p>
    </div>
    """, unsafe_allow_html=True)

    if s2.get("warnings"):
        for w in s2["warnings"]:
            st.markdown(f'<p style="font-family:var(--font-mono);font-size:0.72rem;letter-spacing:0.06em;color:#525252;margin:0.3rem 0">⚠ {w}</p>', unsafe_allow_html=True)

def render_itinerary(s3: dict) -> None:
    _rule(4)
    st.markdown(f"""
    <div style="padding:3rem 0 1.5rem">
        <p style="font-family:var(--font-mono);font-size:0.72rem;letter-spacing:0.18em;text-transform:uppercase;color:var(--muted-fg);margin:0 0 0.8rem">Your Itinerary</p>
        <h2 style="font-family:var(--font-display);font-size:clamp(2rem,5vw,4rem);font-weight:900;letter-spacing:-0.03em;margin:0 0 0.8rem;line-height:1.05">{s3.get("title","")}</h2>
        <p style="font-family:var(--font-body);font-size:1.1rem;line-height:1.7;color:#333;max-width:680px;margin:0">{s3.get("summary","")}</p>
    </div>
    """, unsafe_allow_html=True)

    for day in s3.get("itinerary", []):
        _rule(1)
        st.markdown(f"""
        <div style="padding:2rem 0">
            <div style="display:flex;align-items:baseline;gap:1.5rem;margin-bottom:1.5rem">
                <span style="font-family:var(--font-display);font-size:3.5rem;font-weight:900;letter-spacing:-0.04em;line-height:1">{day.get("day","")}</span>
                <div>
                    <div style="font-family:var(--font-display);font-size:1.3rem;font-weight:700;letter-spacing:-0.02em">{day.get("label","").split("—")[-1].strip() if "—" in day.get("label","") else day.get("label","")}</div>
                    <div style="font-family:var(--font-mono);font-size:0.68rem;letter-spacing:0.1em;text-transform:uppercase;color:var(--muted-fg)">{day.get("estimated_daily_cost","")}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        slot_cols = st.columns(3)
        for col, (slot_label, slot_key) in zip(slot_cols, [("Morning","morning"),("Afternoon","afternoon"),("Evening","evening")]):
            with col:
                st.markdown(f"""
                <div style="border-top:2px solid #000;padding:1rem 0">
                    <div style="font-family:var(--font-mono);font-size:0.65rem;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:0.6rem;color:var(--muted-fg)">{slot_label}</div>
                    <p style="font-family:var(--font-body);font-size:0.95rem;line-height:1.65;margin:0">{day.get(slot_key,"")}</p>
                </div>
                """, unsafe_allow_html=True)

        tips = day.get("tips", [])
        if tips:
            tips_html = "".join(f'<li style="font-family:var(--font-body);font-size:0.875rem;line-height:1.6;color:#333;margin-bottom:0.25rem">{t}</li>' for t in tips)
            st.markdown(f'<ul style="margin:1rem 0 0;padding-left:1.2rem;border-left:2px solid #000">{tips_html}</ul>', unsafe_allow_html=True)

    # Totals + packing
    _rule(4)
    bot_l, bot_r = st.columns([1, 1])
    with bot_l:
        st.markdown(f"""
        <div style="padding:2rem 0">
            <div style="font-family:var(--font-mono);font-size:0.65rem;letter-spacing:0.12em;text-transform:uppercase;color:var(--muted-fg);margin-bottom:0.4rem">Total Estimated Cost</div>
            <div style="font-family:var(--font-display);font-size:2.5rem;font-weight:900;letter-spacing:-0.03em">{s3.get("total_estimated_cost","")}</div>
        </div>
        """, unsafe_allow_html=True)
    with bot_r:
        packing = s3.get("packing_tips", [])
        if packing:
            items = "".join(f'<li style="font-family:var(--font-body);font-size:0.875rem;line-height:1.7;margin-bottom:0.2rem">{p}</li>' for p in packing)
            st.markdown(f"""
            <div style="padding:2rem 0">
                <div style="font-family:var(--font-mono);font-size:0.65rem;letter-spacing:0.12em;text-transform:uppercase;color:var(--muted-fg);margin-bottom:0.8rem">Packing Tips</div>
                <ul style="padding-left:1.2rem;margin:0">{items}</ul>
            </div>
            """, unsafe_allow_html=True)

def render_selfcheck(s4: dict) -> None:
    _rule(2)
    st.markdown(f"""
    <div style="
        background:#000;color:#fff;padding:2.5rem;margin:1.5rem 0;
        position:relative;overflow:hidden;
    ">
        <div style="
            position:absolute;inset:0;
            background-image:repeating-linear-gradient(90deg,transparent,transparent 1px,#fff 1px,#fff 2px);
            background-size:4px 100%;opacity:0.03;pointer-events:none;
        "></div>
        <div style="position:relative">
            <p style="font-family:var(--font-mono);font-size:0.65rem;letter-spacing:0.18em;text-transform:uppercase;color:#aaa;margin:0 0 1.5rem">Self-Check Results</p>
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1.5rem;margin-bottom:1.5rem">
    """, unsafe_allow_html=True)

    scores = s4.get("scores", {})
    score_labels = {
        "budget_respected": "Budget",
        "interests_covered": "Interests",
        "feasibility": "Feasibility",
        "readability": "Readability",
    }
    score_cells = "".join(f"""
        <div>
            <div style="font-family:var(--font-display);font-size:2.8rem;font-weight:900;letter-spacing:-0.04em;line-height:1;color:#fff">{scores.get(k,"—")}<span style="font-size:1rem;font-family:var(--font-mono);opacity:0.5">/10</span></div>
            <div style="font-family:var(--font-mono);font-size:0.62rem;letter-spacing:0.1em;text-transform:uppercase;color:#aaa;margin-top:0.3rem">{label}</div>
        </div>
    """ for k, label in score_labels.items())

    pass_badge = (
        '<span style="background:#fff;color:#000;font-family:var(--font-mono);font-size:0.65rem;letter-spacing:0.1em;text-transform:uppercase;padding:0.3rem 0.8rem">✓ Passed</span>'
        if s4.get("passes")
        else '<span style="border:1px solid #fff;color:#fff;font-family:var(--font-mono);font-size:0.65rem;letter-spacing:0.1em;text-transform:uppercase;padding:0.3rem 0.8rem">✗ Issues Found</span>'
    )

    issues_html = ""
    if s4.get("issues"):
        items = "".join(f'<li style="font-family:var(--font-body);font-size:0.875rem;line-height:1.6;margin-bottom:0.2rem;color:#ccc">{i}</li>' for i in s4["issues"])
        issues_html = f'<ul style="padding-left:1.2rem;margin:1rem 0 0">{items}</ul>'

    st.markdown(f"""
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1.5rem;margin-bottom:1.5rem">
            {score_cells}
        </div>
        <div>{pass_badge}</div>
        {issues_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def main():
    render_hero()
    _rule(4)

    # Initialise session state
    if "result" not in st.session_state:
        st.session_state.result = None   # dict with s1, s3, s4, critical

    # Input area
    st.markdown('<div style="padding:2.5rem 0 1rem">', unsafe_allow_html=True)
    st.markdown(_mono("Describe your trip"), unsafe_allow_html=True)
    raw_text = st.text_area(
        label="trip_input",
        placeholder="e.g. 5 days in Kyoto, love temples and street food, mid budget, vegetarian…",
        height=90,
        key="trip_input",
        label_visibility="collapsed",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        plan_clicked = st.button("Plan my Journey →", key="plan_btn")

    if plan_clicked:
        if not raw_text.strip():
            st.markdown('<p style="font-family:var(--font-mono);font-size:0.75rem;letter-spacing:0.08em;color:#525252;text-align:center;margin-top:1rem">Enter a trip description above.</p>', unsafe_allow_html=True)
            return

        st.markdown('<div style="margin-top:3rem"></div>', unsafe_allow_html=True)
        _rule(4)

        s1 = s2 = s3 = s4 = None

        with st.status("**Stage 1** — Understanding your request…", expanded=False) as status:
            s1 = stage1_understand(raw_text)
            if s1.get("errors"):
                st.warning(f"Input warnings: {', '.join(s1['errors'])}")
            status.update(label="**Stage 1** — Constraints parsed ✦", state="complete", expanded=False)
        render_constraints(s1)
        _scroll_to_bottom()

        with st.status("**Stage 2** — Reasoning about your trip…", expanded=False) as status:
            s2 = stage2_reason(s1)
            status.update(label="**Stage 2** — Day plan reasoned ✦", state="complete", expanded=False)
        render_reasoning(s2)
        _scroll_to_bottom()

        with st.status("**Stage 3** — Writing your itinerary…", expanded=False) as status:
            s3 = stage3_produce(s1, s2)
            status.update(label="**Stage 3** — Itinerary drafted ✦", state="complete", expanded=False)
        _scroll_to_bottom()

        critical = bool(s1.get("errors"))
        if not critical:
            with st.status("**Stage 4** — Self-check in progress…", expanded=False) as status:
                for redo in range(STAGE4_MAX_REDO + 1):
                    s4 = stage4_selfcheck(s1, s3)
                    if not s4.get("redo_required"):
                        break
                    if redo < STAGE4_MAX_REDO:
                        issues = "\n".join(f"- {i}" for i in s4.get("issues", []))
                        st.info(f"Revising itinerary…\n{issues}")
                        s3 = stage3_produce(s1, s2, revision_notes=issues)
                status.update(label="**Stage 4** — Quality check complete ✦", state="complete", expanded=False)
            render_selfcheck(s4)
            _scroll_to_bottom()

        # Persist to session state so download button doesn't wipe the page
        st.session_state.result = {"s1": s1, "s3": s3, "s4": s4, "critical": critical}

    # Render results from session state (survives reruns caused by download button)
    if st.session_state.result:
        r = st.session_state.result
        render_itinerary(r["s3"])

        _rule(1)
        st.markdown('<div style="padding:1.5rem 0">', unsafe_allow_html=True)
        _, dl_col, _ = st.columns([1, 2, 1])
        with dl_col:
            st.download_button(
                label="Download Itinerary JSON →",
                data=json.dumps(r["s3"], indent=2),
                file_name="itinerary.json",
                mime="application/json",
                use_container_width=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # Footer
    _rule(4)
    st.markdown("""
    <div style="padding:2rem 0;display:flex;justify-content:space-between;align-items:center">
        <span style="font-family:var(--font-mono);font-size:0.65rem;letter-spacing:0.12em;text-transform:uppercase;color:var(--muted-fg)">Trip Planner — Prompt Pipeline</span>
        <span style="font-family:var(--font-mono);font-size:0.65rem;letter-spacing:0.08em;color:var(--muted-fg)">4-Stage LLM Chain ✦ OpenRouter</span>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
