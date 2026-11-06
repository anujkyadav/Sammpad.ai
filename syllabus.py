"""
syllabus.py
-----------
Loads the CBSE/KVS Class 11-12 Computer Science split-up syllabus and
builds the system prompt that keeps the chatbot strictly on-syllabus,
with gentle redirection for off-syllabus questions.

Replace SYLLABUS_TEXT below by loading your school's actual split-up
PDF (see load_syllabus_from_pdf()).
"""

import os

# ---------------------------------------------------------------------
# Fallback syllabus summary (replace with your real split-up PDF content)
# ---------------------------------------------------------------------
DEFAULT_SYLLABUS_TEXT = """
CBSE Class 11-12 Computer Science (Code 083) -- Core Topics:

CLASS 11:
- Computer Fundamentals, Encoding Schemes (ASCII, Unicode)
- Python Basics: variables, data types, operators, input/output
- Flow of Control: if-else, loops (for, while)
- Strings, Lists, Tuples, Dictionaries
- Functions in Python (built-in, user-defined, scope)
- Society, Law and Ethics (cyber safety, IPR, digital footprint)

CLASS 12:
- Python Revision Tour, Functions (advanced), File Handling
- Data Structures: Stacks (push/pop operations) using Lists
- Database Concepts, SQL (DDL, DML, aggregate functions, joins)
- Interface Python with SQL (MySQL connectivity)
- Computer Networks: concepts, types, protocols, topologies, network devices
- Data Communication, network case studies
"""


def load_syllabus_from_pdf(pdf_path: str) -> str:
    """
    Loads the official CBSE/KVS split-up syllabus PDF text.
    Requires: pip install pypdf
    """
    from pypdf import PdfReader
    reader = PdfReader(pdf_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def get_syllabus_text() -> str:
    """
    Looks for a local split-up PDF first (data/syllabus.pdf); falls back
    to the built-in summary above if not found.
    """
    from paths import SYLLABUS_PDF_DIR, latest_pdf
    pdf_path = latest_pdf(SYLLABUS_PDF_DIR)   # newest PDF in data/raw_pdfs/syllabus/
    if pdf_path:
        try:
            return load_syllabus_from_pdf(pdf_path)
        except Exception:
            pass
    return DEFAULT_SYLLABUS_TEXT


def build_system_prompt(teacher_name: str = "the PGT Computer Science team") -> str:
    """
    This system prompt is what enforces syllabus restriction AND
    gentle redirection (never a flat refusal) for off-syllabus asks.
    """
    syllabus = get_syllabus_text()
    return f"""You are "sammpad.ai", a friendly AI study companion for CBSE
Class 11-12 Computer Science (Python) students, built by their teacher {teacher_name}.

STRICT RULES:
1. Only answer using topics found in the syllabus below. Do not teach or
   explain anything outside it, even if you know the answer.
2. If a student asks something off-syllabus (e.g. advanced topics, other
   subjects, unrelated chit-chat), do NOT refuse bluntly. Instead, gently
   acknowledge their curiosity in one short sentence, then redirect them
   back to a related syllabus topic they can study instead.
3. Match the real CBSE board exam style when explaining or framing
   examples: MCQs, assertion-reason, output-prediction, fix-the-code,
   stack push/pop operations, SQL output questions, and networking case
   studies.
4. Keep answers concise, exam-focused, and age-appropriate for a
   16-18 year old student.

SYLLABUS (CBSE/KVS Class 11-12 Computer Science):
{syllabus}
"""
