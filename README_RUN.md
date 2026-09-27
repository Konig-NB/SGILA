# SGILA Clean-Machine Run Guide

## Requirements

- Windows 10 or Windows 11
- Python 3.12 or newer
- Internet access for the first dependency installation

## First Run

1. Extract `SGILA_App.zip` to a normal local folder.
2. Open PowerShell or Command Prompt in the extracted `SGILA_App` folder.
3. Run these commands:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py load_curriculum_content
.venv\Scripts\python.exe manage.py sync_grade2_activities
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe manage.py test
.venv\Scripts\python.exe manage.py runserver
```

4. Open `http://127.0.0.1:8000/`.

Alternatively, double-click `run_sgila.bat`. It creates the virtual environment,
installs dependencies, prepares the database, and starts the local server.

## Demo Accounts

All demo accounts use the password `password123`.

- Learner: `learner@sgila.test`
- Grade 3 learner username: `lerato_m`
- Parent: `parent@sgila.test`
- Teacher: `teacher@sgila.test`

All demo learner accounts use the password `password123`.
Demo class codes: `SGILA1`, `RAINB1`, `RAINB2`, `RAINB3`, `RAINB4`, `MKGRD3`, and `MKGRD4`.

**Order matters:** `load_curriculum_content` rewrites each lesson's activities, so
it clears the Grade 2 ones. Always run `sync_grade2_activities` *after* it, never
before. `run_sgila.bat` already does them in that order.

`load_curriculum_content` is safe to run again: it updates the Grade 1-4 lessons
without deleting registered users or their progress. Use `seed_data` only when you
intentionally want to reset the app to its original demo accounts.

## Email and OTP Testing

The clean-machine package uses Django's console email backend by default. OTP and
password-reset messages appear in the terminal. For inbox delivery, copy
`.env.example` to `.env`, set `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD`, then
restart the server. Gmail requires an app password rather than the normal account
password. SMTP is selected automatically when both values are configured.

## Yearly Grade-Confirmation Reminder Emails

At the start of each school year, learners whose grade hasn't been confirmed yet
(see `Child.needs_grade_confirmation()`) show a banner on the parent/teacher
dashboard. On top of that banner, you can email parents a reminder using:

```
python manage.py send_grade_reminders            # sends real emails
python manage.py send_grade_reminders --dry-run   # preview only, sends nothing
```

It's safe to run this as often as you like — each parent gets at most **one**
reminder email per school year (tracked via `Child.grade_reminder_sent_year`), so
running it daily won't spam anyone. It groups multiple children under the same
parent into a single email, and the email always points the parent to `/login`
rather than including a one-click "confirm" link, so the actual grade change stays
behind normal authentication.

This project isn't deployed yet, so nothing schedules this command automatically —
run it however suits wherever you end up hosting it:

- **Cron (Linux/macOS server):** add a line like
  `0 6 1 1 * cd /path/to/sgila_project && /path/to/.venv/bin/python manage.py send_grade_reminders`
  to run at 6am on 1 January. Running it weekly for the first month of the year
  (instead of just once) is a good idea in case the mail server is briefly down.
- **Windows Task Scheduler:** create a task that runs
  `.venv\Scripts\python.exe manage.py send_grade_reminders` with "Start in" set to
  the `sgila_project` folder, triggered on a schedule (e.g. daily during January).
- **Hosting platforms with a scheduler add-on** (Heroku Scheduler, Render Cron
  Jobs, PythonAnywhere scheduled tasks, etc.): point it at the same command —
  `python manage.py send_grade_reminders` — using whichever syntax that platform
  expects.

## Stop the Server

Press `Ctrl+C` in the terminal window.
