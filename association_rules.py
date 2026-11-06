"""
association_rules.py
---------------------
Association Rule Mining over which topics students tend to get wrong
TOGETHER in the same session -- e.g. "students who struggle with
Stacks also tend to struggle with SQL" -> recommend a combined
revision set.

This directly reuses the Day 1 syllabus topic "Association Rules"
(support, confidence, lift) on a genuinely useful classroom question.

Implemented directly with pandas/itertools (no extra ML dependency
needed) so it is easy to install and easy to verify.

IMPORTANT: data/processed/sample_session_logs.csv is SYNTHETIC demo data I
generated to make this feature runnable out of the box. Replace it
with real (anonymized) mistake logs once the app has been used by
actual students -- see log_session_mistakes() below for how real
sessions get appended over time.
"""

import os
import itertools
import pandas as pd

from paths import SESSION_LOG_PATH as LOG_PATH


def load_session_logs() -> pd.DataFrame:
    return pd.read_csv(LOG_PATH)


def log_session_mistakes(student_session: str, topics_missed: list):
    """
    Appends a real session's missed topics to the log file, so the
    association rules improve over time as real students use the app.
    """
    df = load_session_logs()
    new_row = pd.DataFrame([{
        "student_session": student_session,
        "topics_missed": ",".join(topics_missed),
    }])
    updated = pd.concat([df, new_row], ignore_index=True)
    updated.to_csv(LOG_PATH, index=False)


def mine_topic_associations(min_support: float = 0.15, min_confidence: float = 0.5) -> pd.DataFrame:
    """
    Returns 2-item association rules like:
        {Stacks} -> {SQL}   support=0.40  confidence=0.71  lift=1.30
    i.e. "students who miss Stacks questions also tend to miss SQL
    questions -- recommend bundling revision for both."

    support(A,B)     = P(A and B)
    confidence(A->B) = P(B | A) = support(A,B) / support(A)
    lift(A->B)       = confidence(A->B) / support(B)
                       (lift > 1 means A and B co-occur more than chance)
    """
    df = load_session_logs()
    transactions = [set(row.split(",")) for row in df["topics_missed"]]
    n = len(transactions)
    if n == 0:
        return pd.DataFrame(columns=["antecedent", "consequent", "support", "confidence", "lift"])

    all_items = sorted(set().union(*transactions))

    item_support = {
        item: sum(1 for t in transactions if item in t) / n
        for item in all_items
    }

    rules = []
    for a, b in itertools.permutations(all_items, 2):
        pair_count = sum(1 for t in transactions if a in t and b in t)
        support_ab = pair_count / n
        if support_ab < min_support or item_support[a] == 0:
            continue
        confidence = support_ab / item_support[a]
        if confidence < min_confidence:
            continue
        lift = confidence / item_support[b] if item_support[b] > 0 else 0
        rules.append({
            "antecedent": a, "consequent": b,
            "support": round(support_ab, 3),
            "confidence": round(confidence, 3),
            "lift": round(lift, 3),
        })

    result = pd.DataFrame(rules)
    if not result.empty:
        result = result.sort_values("lift", ascending=False).reset_index(drop=True)
    return result
