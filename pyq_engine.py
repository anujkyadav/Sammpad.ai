"""
pyq_engine.py
-------------
Three capabilities, as described in the capstone report:

1. load_pyq_db()              -> structured PYQ dataset
2. get_exact_pyq()            -> direct filter/search, zero AI, zero hallucination
3. generate_similar_question()-> few-shot AI generation grounded in real PYQs
4. cluster_questions()        -> sentence-embeddings + K-Means topic clustering
5. find_similar_questions()   -> cosine-similarity "find similar" feature
6. audit_coverage()           -> simple bias/coverage audit over the PYQ bank
"""

import os
import json
import pandas as pd
import numpy as np

from backend import get_ai_response

from paths import PYQ_DB_PATH as DATA_PATH


# ---------------------------------------------------------------------
# 1. Load
# ---------------------------------------------------------------------

def load_pyq_db() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


# ---------------------------------------------------------------------
# 2. Exact PYQ retrieval -- no AI involved
# ---------------------------------------------------------------------

def get_exact_pyq(df: pd.DataFrame, topic: str = None, question_type: str = None,
                   year: int = None, n: int = 5) -> pd.DataFrame:
    result = df.copy()
    if topic:
        result = result[result["topic"].str.contains(topic, case=False, na=False)]
    if question_type:
        result = result[result["question_type"].str.lower() == question_type.lower()]
    if year:
        result = result[result["year"] == year]
    return result.head(n)


# ---------------------------------------------------------------------
# 3. Few-shot "similar question" generation
# ---------------------------------------------------------------------

def generate_similar_question(df: pd.DataFrame, topic: str, question_type: str,
                               provider: str = "groq", api_key: str = None, model: str = None) -> dict:
    examples = get_exact_pyq(df, topic=topic, question_type=question_type, n=4)
    if examples.empty:
        examples = df[df["question_type"].str.lower() == question_type.lower()].head(4)

    examples_text = "\n\n".join(
        f"Q (Year {r.year}, {r.marks} marks): {r.question_text}\nAnswer: {r.answer}"
        for r in examples.itertuples()
    )

    system_prompt = (
        "You are a CBSE Class 11-12 Computer Science question-paper setter. "
        "Generate ONE new exam question that matches the style, difficulty, "
        "and format of the real past-year questions shown to you. "
        "Return ONLY valid JSON, no extra text, in this exact shape: "
        '{"question": "", "options": [], "correct_answer": "", "explanation": ""} '
        '(leave "options" as an empty list if the question type has no MCQ options.)'
    )
    user_prompt = f"""Topic: {topic}
Question type: {question_type}

Real past-year questions to match the style of:
{examples_text}

Now generate ONE new question of the same type, topic, and difficulty."""

    raw = get_ai_response(system_prompt, user_prompt, provider=provider, api_key=api_key, model=model)

    try:
        cleaned = raw.strip().strip("`").replace("json\n", "", 1)
        return json.loads(cleaned)
    except Exception:
        return {"question": raw, "options": [], "correct_answer": "", "explanation": "(raw model output -- JSON parse failed)"}


# ---------------------------------------------------------------------
# 4 & 5. Embeddings, clustering, similarity search
# ---------------------------------------------------------------------

_embed_model = None


def _get_embedder():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embed_model


def embed_questions(df: pd.DataFrame) -> np.ndarray:
    model = _get_embedder()
    return model.encode(df["question_text"].tolist(), show_progress_bar=False)


def cluster_questions(df: pd.DataFrame, n_clusters: int = 4) -> pd.DataFrame:
    """Adds a 'cluster' column grouping questions by semantic similarity."""
    from sklearn.cluster import KMeans
    embeddings = embed_questions(df)
    n_clusters = min(n_clusters, len(df))
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = km.fit_predict(embeddings)
    out = df.copy()
    out["cluster"] = labels
    return out


def find_similar_questions(df: pd.DataFrame, query_text: str, top_n: int = 3) -> pd.DataFrame:
    from sklearn.metrics.pairwise import cosine_similarity
    model = _get_embedder()
    all_embeddings = embed_questions(df)
    query_embedding = model.encode([query_text])
    sims = cosine_similarity(query_embedding, all_embeddings)[0]
    out = df.copy()
    out["similarity"] = sims
    return out.sort_values("similarity", ascending=False).head(top_n)


def get_cluster_plot_data(df: pd.DataFrame, n_clusters: int = 4):
    """2D PCA projection of clusters, for plotting in the app."""
    from sklearn.decomposition import PCA
    clustered = cluster_questions(df, n_clusters=n_clusters)
    embeddings = embed_questions(df)
    coords = PCA(n_components=2, random_state=42).fit_transform(embeddings)
    clustered["x"] = coords[:, 0]
    clustered["y"] = coords[:, 1]
    return clustered


# ---------------------------------------------------------------------
# 6. Bias / coverage audit
# ---------------------------------------------------------------------

def audit_coverage(df: pd.DataFrame) -> dict:
    """
    Simple, explainable audit:
    - topic distribution (is any topic over/under represented?)
    - question-type distribution
    - year distribution
    """
    return {
        "by_topic": df["topic"].value_counts().to_dict(),
        "by_question_type": df["question_type"].value_counts().to_dict(),
        "by_year": df["year"].value_counts().sort_index().to_dict(),
        "total_questions": len(df),
    }
