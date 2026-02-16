# La Vete - Veterinary Admin Portal

Internal administrative portal for "La Vete", designed to manage inventory, customers, patients, and orders, with WhatsApp automation support.

## Features
- **Product & Inventory Management**: CRUD, stock tracking, atomic movements.
- **Customer & Patient Management**: CRM-like features for pet owners and pets.
- **Order Management**: Internal POS, status workflows, payment tracking.
- **WhatsApp Integration**: Automated queries via n8n (planned).
- **Role-Based Access Control**: Admin, Vet, Cashier roles.

## Tech Stack
- **Backend**: Python 3.10+ with FastAPI
- **Database**: PostgreSQL with SQLAlchemy 2.0 (Async)
- **Frontend**: Jinja2 Templates + Vanilla JS + CSS Variables (Blue/Yellow Theme)

## Setup

1. **Create Virtual Environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Variables**
   Create a `.env` file based on `.env.example`.
   ```bash
   DATABASE_URL=postgresql+asyncpg://user:password@localhost/lavete_db
   SECRET_KEY=your_secret_key
   ```

4. **Run Migrations**
   ```bash
   alembic upgrade head
   ```

5. **Run Server**
   ```bash
   uvicorn app.main:app --reload
   ```

## Project Structure
- `app/api`: API Routers
- `app/core`: Configuration & Security
- `app/models`: Database Models
- `app/templates`: Frontend Templates
- `app/static`: Static Assets
