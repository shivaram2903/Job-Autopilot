# JobPilot AI — Python MVP

JobPilot AI is a local-first Python starter for job discovery, profile-based matching, application tracking, and daily reporting.

## What works in this starter

- Streamlit web dashboard and local SQLite database.
- Resume text extraction from PDF, DOCX, or TXT files.
- Editable candidate profile and preferences.
- Public job discovery from Remotive and Arbeitnow feeds.
- Transparent heuristic match score (skills, target role, location, experience).
- Listing deduplication and saved-job storage.
- Application tracker with status history, notes, follow-up date, and confirmation evidence.
- Optional OpenAI-powered, role-specific resume/cover-letter application pack (user-triggered; facts-only prompt).
- Daily report generation and TXT export.
- Optional SMTP email reports via `.env` and a script that can be scheduled.

## Important limitations

- This is a **single-user local MVP**, not production-ready multi-user software.
- Public feeds do not cover every job board and may have location/category gaps. Remotive is a remote-job feed and requires attribution/linking back to the original listing.
- The job-match score is explainable keyword/rule-based scoring, not an LLM judgement. Optional OpenAI is used only for tailored application-document drafts when explicitly requested.
- This starter **does not automatically submit applications** to LinkedIn, Naukri, Indeed, Glassdoor, or company career portals. Open the original listing, apply through the official site, and then update the tracker with confirmation evidence. Real auto-apply requires separate, permitted integrations for each platform; do not bypass CAPTCHA, MFA, access controls, or site restrictions.
- Daily scheduled email runs only when the operating system or a cloud worker runs `daily_report.py`. Keeping the Streamlit tab open is not a scheduler.

## Install and run (Windows / macOS / Linux)

Use Python 3.10+.

```bash
cd jobpilot_ai
python -m venv .venv
```

Activate the environment:

**Windows PowerShell**
```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux**
```bash
source .venv/bin/activate
```

Install dependencies and start the app:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Streamlit will print a local URL (usually `http://localhost:8501`). Your database and resume files are stored under `data/` by default.

## How to use

1. Open **My Profile** and enter your true skills, experience, target roles, and preferred location.
2. Upload a resume; text is extracted locally and stored in the local database.
3. Open **Discover Jobs**, refresh the public feeds, and filter listings.
4. Add relevant opportunities to your **Application Tracker**.
5. Open each original listing and apply through its supported official process.
6. Update its status and save confirmation evidence in the tracker.
7. Generate and download your daily report.

## Optional AI application document drafts

Set `OPENAI_API_KEY` in `.env` and set `OPENAI_MODEL` to a model available to your API account. A **Generate AI application pack** button appears on job cards. When clicked, the candidate's saved resume text and the selected job description are sent to the configured OpenAI API. The output includes a role-fit summary, tailored resume draft, cover letter, and questions to verify. Review all generated statements before use; generated content is not saved as a submitted application.

## Optional daily email reports

Copy `.env.example` to `.env` and fill in valid SMTP settings. Use an email-provider app password where required. Keep `.env` private; never commit it to source control.

Manual report run:

```bash
python daily_report.py
```

To send the report every day at 9:00 AM India time, use your operating system's scheduler. Examples:

**Linux cron** (ensure the host clock/timezone is configured appropriately):
```cron
0 9 * * * cd /absolute/path/jobpilot_ai && /absolute/path/jobpilot_ai/.venv/bin/python daily_report.py >> data/daily_report.log 2>&1
```

**Windows Task Scheduler:** create a daily task at 9:00 AM. Set the program to the virtual environment's `python.exe`, the argument to `daily_report.py`, and the working directory to the project folder.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Privacy and deployment

The code stores resumes and candidate data locally. Anyone with access to the machine or database file may be able to access them. Before deploying publicly, add proper authentication and per-user authorization, TLS, encrypted private object storage, deletion/export workflows, secret management, dependency scanning, backups, and monitoring. Do not expose the local SQLite database or resume directory through a public static route.

## Source API notes

- Remotive public API: `https://remotive.com/api/remote-jobs`. The API's instructions ask users to link to each original listing and attribute Remotive; it advises against frequent polling. This app applies a local refresh cooldown.
- Arbeitnow feed: `https://www.arbeitnow.com/api/job-board-api`.
