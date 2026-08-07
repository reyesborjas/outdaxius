# Outdaxius

**ES:**  
- Frontend: React + Vite + Tailwind (`frontend`).  
- Backend: FastAPI + SQLAlchemy + PostgreSQL (`backend`).  
- Pasos rápidos:
  1) Frontend → `cd frontend && npm install && npm run dev`
  2) Backend  → `cd backend && python -m venv .venv && .\.venv\Scripts\Activate.ps1 && pip install -r requirements.txt && uvicorn app.main:app --reload`
  3) Base de datos → `docker compose up -d` levanta Postgres y pgAdmin (<http://localhost:5050>). Guía completa: [docs/PGADMIN_SETUP.md](docs/PGADMIN_SETUP.md)

**EN:**  
- Frontend: React + Vite + Tailwind (`frontend`).  
- Backend: FastAPI + SQLAlchemy + PostgreSQL (`backend`).  
- Quick steps:
  1) Frontend → `cd frontend && npm install && npm run dev`
  2) Backend  → `cd backend && python -m venv .venv && .\.venv\Scripts\Activate.ps1 && pip install -r requirements.txt && uvicorn app.main:app --reload`
  3) Database → `docker compose up -d` brings up Postgres and pgAdmin (<http://localhost:5050>). Full guide: [docs/PGADMIN_SETUP.md](docs/PGADMIN_SETUP.md)
