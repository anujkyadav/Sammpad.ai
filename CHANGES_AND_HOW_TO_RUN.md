# Practise: local run and resolved issues

## Run locally (Windows PowerShell)

1. From the repository root, create and activate a Python 3.11 environment:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -e .
   ```

2. If you do not already have a local `.env`, copy the template and fill in the credentials:

   ```powershell
   Copy-Item .env.example .env
   ```

   `DATABASE_URL`, `AWS_ENDPOINT_URL_S3`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
   `AWS_REGION`, and `AWS_BUCKET_NAME` are required for Neon database and object storage.
   Set an AI provider key such as `API_KEY_GROQ_ANUJ` to enable AI features. Never commit
   `.env` or real credentials.

3. Start the app:

   ```powershell
   streamlit run Practise.py
   ```

   The browser opens the Practise home page. To use the Code Sandbox, separately deploy
   the Docker-based executor described in `README.md`, then configure
   `CODE_EXECUTOR_URL` and `CODE_EXECUTOR_TOKEN`. Code execution stays disabled without it.

## Issues from the earlier review that have been addressed

- **Cluttered project root:** application modules are grouped under `src/saampad_ai/`;
  Streamlit screens remain in `pages/`, and `Practise.py` is the entry point.
- **Wrong syllabus could be selected by file date:** syllabus PDFs are uploaded to object
  storage, explicitly selected as active, and validated before activation. The app no
  longer chooses the newest local PDF automatically.
- **Unsafe in-process code execution:** the Streamlit app no longer executes submitted
  Python with `exec`. It can send code to a separate executor that runs each job in a
  disposable Docker container with network access disabled and CPU, memory, process,
  time, and output limits. The runner is off until configured.
- **Question-bank data integrity and concurrent writes:** questions are validated before
  storage, saved in Postgres using database transactions, and duplicate question text is
  skipped by a database uniqueness constraint.
- **Upload overwrites and size handling:** uploads use generated unique object keys, and
  Streamlit's configured upload limit is 20 MB.
- **Non-persistent chat and practice history:** chat messages and quiz attempts are stored
  in Neon Postgres and can be restored for the same anonymous session.
- **Local-only runtime data:** question and session records use Neon Postgres; uploaded
  files and the classifier artifact use Neon Object Storage.
- **Hard-to-read UI and exposed implementation details:** the app uses a consistent dark
  theme with legible text and controls, and user-facing errors avoid showing raw
  tracebacks or internal storage paths.
- **Settings and uploads mixed together:** API provider/model settings are on **Settings**;
  file management is on **Uploads**.
- **Generic Streamlit sidebar label:** the main entry point is named `Practise.py`, so
  Streamlit displays **Practise** in its default page navigation.

## Remaining deployment considerations

- Sessions are anonymous and identified through IDs in the page URL. Anyone who has a
  session link can access that session; there is no account-based authentication yet.
  Avoid entering sensitive personal information or sharing session links.
- The Docker executor is a separate service and is not started by Streamlit Community
  Cloud. Docker containers share the host kernel; the executor host should be isolated
  from the app and database. See `README.md` for its deployment requirements.
- The app requires valid Neon database and object-storage credentials at startup; it does
  not fall back to local storage.
- Python input validation and container resource limits reduce risk but do not guarantee
  complete isolation. Higher-risk public execution may require a stronger runtime such as
  gVisor or Kata Containers.
