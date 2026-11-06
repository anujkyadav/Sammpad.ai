"""
classifier.py
-------------
A genuinely self-trained supervised ML model (NOT an LLM call) that
learns to predict a question's TOPIC from its text, trained entirely
on your own pyq_database.csv using scikit-learn.

This directly reuses Day 1 syllabus skills (supervised learning,
train/test split, model evaluation) applied to a real, useful task:
auto-tagging a freshly pasted question with its likely topic, so a
teacher can drop in a new question without manually labelling it.

Train it with:
    python train_classifier.py

Then use predict_topic() anywhere in the app.
"""

import os
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.pipeline import Pipeline

from paths import CLASSIFIER_PATH as MODEL_PATH


def train_topic_classifier(df: pd.DataFrame, save: bool = True) -> dict:
    """
    Trains a TF-IDF + Logistic Regression pipeline to predict `topic`
    from `question_text`. Returns a small report dict so the app can
    display real accuracy numbers to evaluators -- not a canned claim.
    """
    X = df["question_text"]
    y = df["topic"]

    # With a small demo dataset, stratified split can fail if a class
    # has too few samples -- fall back to a plain split in that case.
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=42, stratify=y
        )
    except ValueError:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=42
        )

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
        ("clf", LogisticRegression(max_iter=1000)),
    ])
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, zero_division=0)

    if save:
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(pipeline, MODEL_PATH)

    return {
        "accuracy": acc,
        "report": report,
        "train_size": len(X_train),
        "test_size": len(X_test),
        "classes": sorted(y.unique().tolist()),
    }


def load_topic_classifier():
    if not os.path.exists(MODEL_PATH):
        return None
    return joblib.load(MODEL_PATH)


def predict_topic(question_text: str) -> dict:
    """
    Predicts the likely topic of a new, freely pasted question using
    the self-trained model -- no AI/LLM call involved here at all.
    """
    model = load_topic_classifier()
    if model is None:
        return {"error": "Model not trained yet. Run: python train_classifier.py"}

    pred = model.predict([question_text])[0]
    proba = model.predict_proba([question_text])[0]
    classes = model.named_steps["clf"].classes_
    confidence = dict(sorted(zip(classes, proba), key=lambda x: -x[1]))

    return {
        "predicted_topic": pred,
        "confidence": {k: round(float(v), 3) for k, v in list(confidence.items())[:3]},
    }
