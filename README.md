# La Vete - Veterinary Admin Portal

Internal administrative portal for **"La Vete"**, designed to streamline operations by managing inventory, customers, patients, and orders. The system features a modern, responsive UI and integrates with WhatsApp for automated customer communication.

## 🚀 Features

- **Product & Inventory Management**: 
  - Complete CRUD operations.
  - Stock tracking with atomic movements.
  - Image support and JSON Import/Export.
- **Customer & Patient CRM**: 
  - Manage owners and their pets (Dogs, Cats, etc.) with medical notes.
  - Order history and contact details.
- **Order Management (POS)**: 
  - Create orders, add items, and track payment status (Pending, Paid, Delivered).
  - Print-friendly views and status workflows.
- **WhatsApp Integration** (In Development): 
  - Automated queries via n8n and Meta API.
- **Role-Based Access Control**: 
  - Secure login with JWT Authentication.
  - Admin and Staff roles.

## 🛠 Tech Stack

- **Backend**: Python 3.10+ with [FastAPI](https://fastapi.tiangolo.com/)
- **Database**: PostgreSQL (Production) / SQLite (Dev) with [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (Async)
- **Frontend**: Server-Side Rendering with Jinja2 Templates + Vanilla JS
- **Styling**: Custom CSS ensuring a responsive, Blue/Yellow branded theme.

## 📦 Setup & Installation

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd lavete
   ```

2. **Create Virtual Environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**
   Create a `.env` file based on `.env.example`.
   ```bash
   cp .env.example .env
   # Edit .env with your specific configuration
   ```

   **Database Options**:
   
   - **Option A: SQLite (Default / Local Dev)**
     ```bash
     DATABASE_URL=sqlite+aiosqlite:///./lavete.db
     ```
   
   - **Option B: AWS Lightsail Managed Database (PostgreSQL - Production)**
     ```bash
     DATABASE_URL=postgresql+asyncpg://dbmasteruser:password@ls-xxx.region.rds.amazonaws.com:5432/dbmaster
     ```

5. **Run Migrations**
   ```bash
   alembic upgrade head
   ```

6. **Run Server**
   ```bash
   uvicorn app.main:app --reload
   ```

## 🚀 Deployment

For detailed deployment instructions on AWS Lightsail, please refer to [DEPLOYMENT.md](DEPLOYMENT.md).

## 📂 Project Structure

- `app/api`: API Routers and Endpoints.
- `app/core`: Configuration, Security, and Database connections.
- `app/models`: SQLAlchemy Database Models.
- `app/schemas`: Pydantic Schemas for data validation.
- `app/services`: Business logic layer.
- `app/templates`: Jinja2 Frontend Templates.
- `app/static`: Static Assets (CSS, JS, Images).
