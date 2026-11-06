"""Streamlit rendering helpers shared by app.py and the Settings page."""
import re
import streamlit as st

NAVY = "#1F3864"

TEAM = [
    "Mr. Anuj Kumar, PGT CS",
    "Mr. Dipayan Sarkar, PGT CS",
    "Mr. Arkopal Ray, PGT CS",
    "Ms. Payal Bhattacharjee, PGT CS",
    "Ms. Mohana Bakshi, PGT CS",
    "Ms. Madhulika Debnath, PGT CS",
    "Mr. Aftab Alam Shahnawaz, PGT CS",
]

GLOBAL_CSS = f"""
<style>
.stApp {{ background-color: #FFFFFF; }}
h1, h2, h3 {{ color: {NAVY}; }}
.stButton>button, .stFormSubmitButton>button {{ background-color: {NAVY}; color: white; border-radius: 6px; }}
section[data-testid="stSidebar"] {{ background-color: #F2F5FA; }}
/* Python code: Consolas / Courier New everywhere */
code, pre, [data-testid="stCode"] *, .stTextArea textarea {{
    font-family: Consolas, "Courier New", monospace !important;
}}
[data-testid="stCode"] pre {{ font-size: 0.95rem; line-height: 1.45; }}
.ar-line {{ margin: 0.15rem 0; }}
.opt-good {{ color: #1B7F3B; font-weight: 600; }}
.opt-bad  {{ color: #B3261E; font-weight: 600; }}
.opt-plain {{ color: #333; }}
</style>
"""


def apply_style():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def sidebar_branding():
    import os
    from paths import ROOT
    logo = os.path.join(ROOT, "logo.png")
    with st.sidebar:
        if os.path.exists(logo):
            st.image(logo, width=110)
        st.markdown("### sammpad.ai")
        st.caption("Helper for Class 12 Computer Science")
        st.markdown("**Computer Science Team**")
        st.markdown("\n".join(f"{i}. {n}" for i, n in enumerate(TEAM, 1)))


def esc(text: str) -> str:
    """Escape characters Streamlit markdown would otherwise interpret."""
    return re.sub(r"([\\`*_{}\[\]<>#~$|])", r"\\\1", str(text))


def render_question(p: dict, number=None, meta: str = ""):
    """Question text on the first line, then code (monospace), then Assertion / Reason lines."""
    prefix = f"**Q{number}.** " if number else ""
    if p["kind"] == "ar":
        st.markdown(f"{prefix}{esc(p['stem'])}")
        st.markdown(f"<div class='ar-line'><b>Assertion (A):</b> {_html(p['assertion'])}</div>"
                    f"<div class='ar-line'><b>Reason (R):</b> {_html(p['reason'])}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"{prefix}{esc(p['stem'])}")
        if p.get("code"):
            st.code(p["code"], language="python")
        if p.get("tail"):
            st.markdown(esc(p["tail"]))
    if meta:
        st.caption(meta)


def _html(t: str) -> str:
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def option_label(letter: str, text: str) -> str:
    return f"({letter}) {esc(text)}"


def render_review_options(options: dict, correct, chosen):
    """One option per line, marked right/wrong after submission."""
    for k, v in options.items():
        txt = _html(f"({k}) {v}")
        if k == correct:
            st.markdown(f"<div class='opt-good'>✅ {txt}{' &nbsp;(your answer)' if chosen == k else ''}</div>", unsafe_allow_html=True)
        elif k == chosen:
            st.markdown(f"<div class='opt-bad'>❌ {txt} &nbsp;(your answer)</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='opt-plain'>&nbsp;&nbsp;&nbsp;&nbsp;{txt}</div>", unsafe_allow_html=True)
