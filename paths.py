"""Central place for every data path used by sammpad.ai."""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")

RAW_PDF_DIR = os.path.join(DATA_DIR, "raw_pdfs")        # untouched input PDFs
PYQ_PDF_DIR = os.path.join(RAW_PDF_DIR, "pyq")           # past-year question papers
SYLLABUS_PDF_DIR = os.path.join(RAW_PDF_DIR, "syllabus")  # latest syllabus PDF(s)
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")      # CSVs, trained models, logs

PYQ_DB_PATH = os.path.join(PROCESSED_DIR, "pyq_database.csv")
CLASSIFIER_PATH = os.path.join(PROCESSED_DIR, "topic_classifier.joblib")
SESSION_LOG_PATH = os.path.join(PROCESSED_DIR, "sample_session_logs.csv")

for _d in (PYQ_PDF_DIR, SYLLABUS_PDF_DIR, PROCESSED_DIR):
    os.makedirs(_d, exist_ok=True)


def latest_pdf(folder: str):
    """Newest PDF in a folder, or None."""
    pdfs = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".pdf")]
    return max(pdfs, key=os.path.getmtime) if pdfs else None
