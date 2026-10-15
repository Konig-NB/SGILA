# SGILA Clean-Machine Run Guide

## Deploying on Render

The repository includes a Render Blueprint (`render.yaml`) for the Django web
service. It installs the requirements and collects static files during the
build; each web-service start runs database migrations before starting Gunicorn.
The Blueprint does not create a database or choose a paid service plan. Before
the first deploy, provide `DJANGO_SECRET_KEY` and `DATABASE_URL` in Render's
environment settings. Connect an existing PostgreSQL database and use its
connection URL for `DATABASE_URL`. Production requires a secret key and
PostgreSQL configuration; outside the Blueprint, either `DATABASE_URL` or the
component `DB_NAME`, `DB_USER`, and `DB_PASSWORD` variables can supply that
configuration. Do not use the local SQLite file for a hosted deployment.

Render's `RENDER_EXTERNAL_HOSTNAME` is automatically allowed as a host and
trusted HTTPS origin. If you add a custom domain, add its hostname to
`DJANGO_ALLOWED_HOSTS` and its HTTPS origin (for example,
`https://app.example.org`) to `DJANGO_CSRF_TRUSTED_ORIGINS`. Set `SITE_URL` to
the public HTTPS URL if email links should use a custom domain. Configure email
and any optional AI provider credentials separately in the service environment;
never put production credentials in this repository.

The DBE schools master-list CSV/XLSX is external data and is not included in the
repository or the deployment. After the database is connected, make the source
file available to the running service using an authorized runtime file-transfer
method, then run the importer once from the service environment, for example:

```sh
python manage.py import_schools /path/to/National-schools.csv
```

The command accepts the DBE semicolon-delimited CSV and the normalized CSV/XLSX
formats described in the Enterprise School Search section below. A fresh
database also needs the curriculum content loaded once; run
`python manage.py load_curriculum_content` followed by
`python manage.py sync_grade2_activities` from the service environment. Do not
run the local demo-account seeder on a production database. Confirm the selected
Render service/database plans and their costs in Render before creating or
connecting services. This repository change does not create Render resources.

Render's local filesystem is ephemeral by default. Child profile photos and
generated story images saved under `media/` can be lost when the service is
replaced or redeployed. Configure persistent media storage before relying on
those uploads in production; this Blueprint intentionally does not attach a
paid disk or provision a storage service.

## Requirements

- Windows 10 or Windows 11
- Python 3.12 or newer
- Internet access for the first dependency installation

## First Run

1. Extract `SGILA_App.zip` to a normal local folder.
2. Open PowerShell or Command Prompt in the extracted `SGILA_App` folder.
3. Install and start PostgreSQL, then create a database and login role. For
   example, in `psql` (enter the role password at the prompt):

```sql
CREATE ROLE sgila_user LOGIN;
\password sgila_user
CREATE DATABASE sgila_db OWNER sgila_user;
```

4. Copy `.env.example` to `.env` and set `DB_NAME`, `DB_USER`, and
   `DB_PASSWORD` to match the PostgreSQL database and role you created.
   `DB_HOST` and `DB_PORT` default to `localhost` and `5432` in the settings;
   change them if your PostgreSQL server uses a different address. Keep `.env`
   private and do not commit it.
5. Run these commands:

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

6. Open `http://127.0.0.1:8000/`.

PostgreSQL is the default database. To keep using SQLite for a local-only
development run, set `DB_ENGINE=sqlite` in `.env`; no PostgreSQL credentials
are needed in that mode. SQLite is not supported when `DJANGO_DEBUG=False`.

### Moving Existing SQLite Data to PostgreSQL

Back up `db.sqlite3` before starting. The Django fixture commands below copy
database records only; copy the `media/` files separately if the database
contains uploaded-file paths. For the export, set `DB_ENGINE=sqlite` and
temporarily remove or comment out `DATABASE_URL` in `.env` if it is set
(`DATABASE_URL` takes precedence over `DB_ENGINE`). Store the fixture somewhere
private outside the repository (it may contain personal data):

```powershell
.venv\Scripts\python.exe manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.permission --indent 2 --output C:/secure-backup/sgila-data.json
```

Then configure `.env` for PostgreSQL (`DB_ENGINE=postgresql`, `DB_NAME`,
`DB_USER`, `DB_PASSWORD`, and, if needed, `DB_HOST`/`DB_PORT`) and run:

```powershell
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py loaddata C:/secure-backup/sgila-data.json
```

Verify the migrated users and application data before retiring the SQLite
backup. This fixture workflow should be tested on a backup first for any
project-specific data or customizations; it does not migrate uploaded files or
database-server settings.

Alternatively, double-click `run_sgila.bat`. It creates the virtual environment,
installs dependencies, prepares the database, and starts the local server.

## Enterprise School Search

Enterprise school search uses the imported DBE school list. On a fresh database,
load the list before using the Enterprise finder:

```powershell
python manage.py import_schools "C:/path/to/National schools.csv"
```

The importer accepts the DBE semicolon-delimited school list as well as the
project's normalized CSV format. The source list is not bundled with SGILA.

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
password-reset messages appear in the terminal; Help Center tickets are saved,
but their support notification and confirmation email are not sent. The ticket
API returns `201` when the ticket is saved, so check `confirmation_email_sent`
(and `support_notification_sent`) to tell whether the emails were accepted for
delivery.

For inbox delivery, copy `.env.example` to `.env`, replace the example values,
and restart the server. Set `EMAIL_HOST_USER` to the SMTP account and
`EMAIL_HOST_PASSWORD` to its valid SMTP credential. For Gmail, use an App
Password (not the normal account password; Google account 2-Step Verification
must be enabled). Also set `DEFAULT_FROM_EMAIL` to an address allowed by that
SMTP account and `SUPPORT_EMAIL` to the mailbox that should receive help
requests. The example password is a placeholder and does not enable SMTP;
without a usable credential, SGILA selects the console backend.

A `*_sent: true` response means the configured email backend accepted the
message, not that it reached the recipient's inbox. SMTP provider policy,
recipient filtering, and spam handling can still affect final delivery.

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
