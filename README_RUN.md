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

`load_curriculum_content` is safe to run again: it updates the Grade 1-4 lessons
without deleting registered users or their progress. Use `seed_data` only when you
intentionally want to reset the app to its original demo accounts.

## Email and OTP Testing

The clean-machine package uses Django's console email backend by default. OTP and
password-reset messages appear in the terminal. For inbox delivery, copy
`.env.example` to `.env`, set `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD`, then
restart the server. Gmail requires an app password rather than the normal account
password. SMTP is selected automatically when both values are configured.

## Stop the Server

Press `Ctrl+C` in the terminal window.
