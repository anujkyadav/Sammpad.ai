"""
train_classifier.py
--------------------
Run this once (and again any time you expand data/processed/pyq_database.csv)
to train the self-trained topic classifier.

Usage:
    python train_classifier.py
"""

from pyq_engine import load_pyq_db
from classifier import train_topic_classifier

if __name__ == "__main__":
    df = load_pyq_db()
    print(f"Training on {len(df)} questions across {df['topic'].nunique()} topics...")

    result = train_topic_classifier(df)

    print(f"\nTrain size: {result['train_size']}  |  Test size: {result['test_size']}")
    print(f"Test accuracy: {result['accuracy']:.2%}")
    print("\nClassification report:")
    print(result["report"])
    print("\nModel saved to data/processed/topic_classifier.joblib")
    print("\nNOTE: Accuracy here is limited by how many examples exist PER TOPIC,")
    print("not just the total row count -- with 12+ topic classes, many still have")
    print("only 1-3 training examples each. This is EXPECTED and genuinely worth")
    print("showing live: more real PYQs per topic (especially for the thin classes)")
    print("will visibly raise accuracy on retraining -- a concrete, honest")
    print("demonstration of how training data size affects a model.")
