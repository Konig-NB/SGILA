# SGILA Reading App

Clean Django web application for SGILA foundation phase reading.

## What Is Included

- Web app pages for learner, parent, and teacher flows
- Lerato's Fruit Basket lesson
- Parent and teacher dashboards
- Learner progress report dashboard
- Teacher class codes
- Parent/learner class-code linking
- API endpoints for lessons, activities, scoring, and progress

## Quick Start

```bash
pip install django djangorestframework
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Demo Logins

All demo accounts use:

```text
password123
```

Learner:

```text
sipho_d
```

Parent:

```text
parent@sgila.test
```

Teacher:

```text
teacher@sgila.test
```

## Demo Class Codes

Teacher general code:

```text
SGILA1
```

Grade 1 class code:

```text
RAINB1
```

Grade 2 class code:

```text
RAINB2
```

Parents can enter a class code when adding a child. Learners can also enter a class code during learner registration.

## Useful Commands

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py seed_data
```

## Main Folders

```text
api/                 Django models, API views, tests, admin, seed data
lessons/             Web page views and routes
templates/           HTML templates
static/css/          App styling
static/img/          Koaly, Lerato, and lesson assets
static/diagrams/     UI flow diagrams and PDFs
```
