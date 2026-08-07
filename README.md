# StudyPal Backend

Django REST API for **StudyPal** — notebooks, notes, flashcards, and quizzes with JWT auth and Gemini-assisted study features.

**Frontend:** [StudyPal_Frontend](https://github.com/Amaankaa/StudyPal_Frontend) · **Live:** https://study-pal-frontend-one.vercel.app

## Stack

- **Django** + **Django REST Framework**
- **PostgreSQL** (via `dj-database-url` / Render)
- **JWT** (`djangorestframework-simplejwt`)
- **CORS** + **WhiteNoise** + **Gunicorn**
- **Google Generative AI** for study assistance

## Quick start

```bash
git clone https://github.com/Amaankaa/studypal-backend.git
cd studypal-backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # if present — set SECRET_KEY, DATABASE_URL, etc.
python manage.py migrate
python manage.py runserver
```

## Deploy

Configured for [Render](https://render.com) via `render.yaml` (`studypal.onrender.com`).

## Related

- Frontend: https://github.com/Amaankaa/StudyPal_Frontend