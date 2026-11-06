"""Settings page: AI provider/model/key + question-paper & syllabus upload and conversion."""
import os
import sys
import pandas as pd
import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_config import PROVIDERS, DEFAULT_PROVIDER, env_key, get_ai_config
from paths import ROOT, PYQ_PDF_DIR, SYLLABUS_PDF_DIR, PYQ_DB_PATH
from pdf_to_pyq import parse_pdf_to_dataframe, append_to_database
from ui_components import apply_style, sidebar_branding

LOGO = os.path.join(ROOT, "logo.png")
st.set_page_config(page_title="Settings · sammpad.ai", page_icon=LOGO if os.path.exists(LOGO) else "⚙️", layout="wide")
apply_style()
sidebar_branding()
st.title("⚙️ Settings")

tab_ai, tab_upload = st.tabs(["🤖 AI Settings", "📄 Upload Question Paper / Syllabus"])

# ----------------------------- AI SETTINGS -----------------------------
with tab_ai:
    names = list(PROVIDERS)
    st.session_state.setdefault("ai_provider", DEFAULT_PROVIDER)
    provider = st.selectbox("Model provider", names, index=names.index(st.session_state.ai_provider))
    if provider != st.session_state.ai_provider:         # switching provider resets the model to its default
        st.session_state.ai_model = PROVIDERS[provider]["model"]
    st.session_state.ai_provider = provider
    st.session_state.setdefault("ai_model", PROVIDERS[provider]["model"])
    st.session_state.ai_model = st.text_input("Model", value=st.session_state.ai_model,
                                              help=f"Default for {provider}: {PROVIDERS[provider]['model']}")
    if env_key(provider):
        st.success(f"API key loaded from environment variable `{PROVIDERS[provider]['env']}`.")
    else:
        st.warning(f"Environment variable `{PROVIDERS[provider]['env']}` is not set. "
                   "Set it before starting the app, or paste a key below (kept only for this browser session).")
        st.session_state.ai_key_override = st.text_input("API key (optional)", type="password")
    cfg = get_ai_config(st.session_state)
    st.caption(f"Active: **{cfg['provider']}** · **{cfg['model']}** · key {'✔ found' if cfg['api_key'] else '✘ missing'}")

# ----------------------------- UPLOADS -----------------------------
with tab_upload:
    st.caption(f"PDFs are saved untouched in `data/raw_pdfs/`. Reviewed questions go to the processed "
               f"database `data/processed/pyq_database.csv`.")
    kind = st.radio("What are you uploading?", ["Past-year question paper", "Latest syllabus"], horizontal=True)
    target = PYQ_PDF_DIR if kind.startswith("Past") else SYLLABUS_PDF_DIR
    up = st.file_uploader("Upload PDF", type=["pdf"])
    if up and st.button("💾 Save PDF to data folder"):
        with open(os.path.join(target, os.path.basename(up.name)), "wb") as f:
            f.write(up.getbuffer())
        st.success(f"Saved to data/raw_pdfs/{'pyq' if target == PYQ_PDF_DIR else 'syllabus'}/{up.name}")
        if target == SYLLABUS_PDF_DIR:
            st.info("The newest PDF in the syllabus folder is used by the chat assistant automatically.")

    if kind.startswith("Past"):
        st.markdown("### Convert a saved question paper into PYQ questions")
        pdfs = sorted(f for f in os.listdir(PYQ_PDF_DIR) if f.lower().endswith(".pdf"))
        if not pdfs:
            st.info("No PDFs in data/raw_pdfs/pyq/ yet. Upload one above or copy files there.")
        else:
            c1, c2 = st.columns([2, 1])
            chosen = c1.selectbox("Question paper", pdfs)
            year = c2.number_input("Exam year", 2015, 2035, 2025)
            if st.button("🔍 Extract & Structure Questions", disabled=not cfg["api_key"]):
                bar = st.progress(0, text="Starting...")
                try:
                    st.session_state.parsed_df = parse_pdf_to_dataframe(
                        os.path.join(PYQ_PDF_DIR, chosen), int(year), cfg["provider"], cfg["api_key"],
                        progress_callback=lambda d, t: bar.progress(d / t, text=f"Parsing chunk {d} of {t}..."),
                        model=cfg["model"])
                    bar.empty()
                    if st.session_state.parsed_df.empty:
                        st.warning("No questions identified. The PDF may be a scanned image, or try again.")
                except Exception as e:
                    bar.empty()
                    st.error(f"Could not process this PDF: {e}")
            if not cfg["api_key"]:
                st.caption("Configure an API key in the AI Settings tab to enable extraction.")

        df = st.session_state.get("parsed_df")
        if df is not None and not df.empty:
            st.markdown("#### Review & edit before saving")
            edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, height=400, column_config={
                "question_type": st.column_config.SelectboxColumn(options=[
                    "MCQ", "Assertion-Reason", "Output-Prediction", "Fix-the-Code", "Case-Study", "Short-Answer", "Long-Answer"])})
            if st.button("💾 Save approved questions to database", type="primary"):
                clean = edited.dropna(subset=["question_text"])
                clean = clean[clean["question_text"].str.strip() != ""]
                res = append_to_database(clean, PYQ_DB_PATH)
                st.success(f"Added {res['added']} question(s) ({res['duplicates_skipped']} duplicate(s) skipped). "
                           f"Database now has {res['total']}.")
                st.info("Tip: re-run `python train_classifier.py` to retrain the topic classifier.")
                st.session_state.parsed_df = None
                st.cache_data.clear()
