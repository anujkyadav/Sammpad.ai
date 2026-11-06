# sammpad.ai — Helper for Class 12 Computer Science

Streamlit app: syllabus-restricted chat, PYQ practice (MCQ / Assertion-Reason quiz), smart-practice agent, code sandbox, teacher tools.

## Run
```bash
pip install -r requirements.txt
export API_KEY_GROQ_ANUJ="..."      # default provider (model: openai/gpt-oss-20b)
export API_KEY_GEMINI_ANUJ="..."    # optional (model: gemini-3.1-flash-lite)
streamlit run app.py
```
(Windows PowerShell: `$env:API_KEY_GROQ_ANUJ="..."`.) A `.env` file also works.

## AI configuration
No API selection on the main page. Open **Settings → AI Settings** to change provider/model. Default is **groq**; keys are read from the environment variables above. Defaults are defined in `ai_config.py`.

## Settings → Upload
Upload a past-year paper or the latest syllabus PDF. Papers can then be converted to questions (AI extraction → review table → save).

## Folders
```
data/
├── raw_pdfs/
│   ├── pyq/        <- put past-year question-paper PDFs here
│   └── syllabus/   <- put the latest syllabus PDF here (newest file is used by the chat)
└── processed/      <- pyq_database.csv, topic_classifier.joblib, session logs
logo.png            <- replace with your own logo (used in sidebar, chat avatar, browser tab)
```
After adding many questions run `python train_classifier.py` to retrain the topic classifier.

## PYQ's Practice
* **MCQ & Assertion-Reason Quiz**: ~10 questions per round, one option per line, Assertion and Reason on separate lines, Python code in a Consolas/Courier New block. Submit any time (unanswered allowed); results show correct/wrong, the answer key and an optional "Explain with AI".
* **Single question**: any question type, exact PYQ or AI-generated.
* Code in questions stored on one line is re-indented automatically (best effort). For perfect layout store code with real line breaks in the CSV cell.
