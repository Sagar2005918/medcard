# National Healthcare ID System

A **FastAPI + PostgreSQL (Neon)** backend that gives every Indian citizen a unique, lifelong **Health-ID** — similar to Aadhaar but for healthcare.

---

## 🏗 Architecture

```
┌────────────────────────────────────────────────────────┐
│                    RENDER (Docker)                      │
│                                                        │
│  FastAPI (Gunicorn + Uvicorn workers)                  │
│   /api/auth      – login, register hospital, /me       │
│   /api/admin     – approve hospitals, create citizens  │
│   /api/citizens  – health profiles, vitals, visits     │
│   /api/insurance – policy balances, claims             │
│   /api/public    – QR/Health-ID verification           │
└──────────────────┬─────────────────────────────────────┘
                   │  asyncpg (async PostgreSQL driver)
                   ▼
        ┌─────────────────────┐
        │   NEON (PostgreSQL) │
        └─────────────────────┘
```

## 👥 Database Roles

| Role | Description |
|------|-------------|
| `ADMIN` | Super-admin: approves hospitals, creates citizen profiles |
| `GOV_APPROVED_HOSPITAL` | Can update vitals + run periodic checkups (every 3–5 months) |
| `STANDARD_HOSPITAL` | Can read citizen records and log medical visits |
| `CITIZEN` | Can view own profile and insurance details |

---

## 🚀 Quick Start (Local Dev)

### 1. Get a Neon Database

1. Sign up at [neon.tech](https://neon.tech) (free tier available)
2. Create a new project → copy the **Connection string** (it looks like `postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require`)

### 2. Configure environment

```bash
cd python/
cp .env .env.local    # optional backup
```

Edit `python/.env` and set your Neon URL:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require
JWT_SECRET=your-secure-random-secret
JWT_EXPIRES_IN=7d
```

### 3. Install dependencies

```bash
pip install -r python/requirements.txt
```

### 4. Seed demo data

```bash
cd python/
python3 seed.py
```

Output:
```
✅  Seed complete!
   Health-ID  : 1234-5678-9012
   Admin      : admin / Admin@123
   Gov hosp   : govhospital / Hospital@123
   Std hosp   : stdhospital / Hospital@123
   Citizen    : John Doe
   Insurance  : Ayushman Bharat ₹5,00,000
```

### 5. Run the server

```bash
cd python/
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/docs** for the interactive Swagger UI.

---

## ☁️ Deploy to Render + Neon

### Step 1 – Push to GitHub

```bash
git add .
git commit -m "healthcare id system"
git push origin main
```

### Step 2 – Create Neon database

Already done? Skip. Otherwise go to [neon.tech](https://neon.tech) and copy the connection string.

### Step 3 – Create Render Web Service

1. Go to [render.com](https://render.com) → **New → Web Service**
2. Connect your GitHub repo
3. Render auto-detects `render.yaml`
4. In the **Environment** tab, set:
   - `DATABASE_URL` → your Neon connection string
   - `JWT_SECRET` → auto-generated (render.yaml already handles this)
5. Click **Deploy**

Tables are created automatically on first startup via `Base.metadata.create_all`.

### Step 4 – Seed production data

After the service is live, run the seed script locally pointing at your Neon DB:

```bash
cd python/
DATABASE_URL="<your-neon-url>" python3 seed.py
```

---

## 📡 API Endpoints

### Authentication (`/api/auth`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/login` | Login → returns JWT |
| `POST` | `/api/auth/register_hospital` | Self-register a hospital (Admin must approve) |
| `GET`  | `/api/auth/me` | Current user info |

### Admin (`/api/admin`) — requires `ADMIN` role

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/admin/hospitals/pending` | List hospitals awaiting approval |
| `POST` | `/api/admin/hospitals/{id}/approve` | Approve a hospital |
| `POST` | `/api/admin/hospitals/{id}/reject` | Reject with reason |
| `POST` | `/api/admin/citizens` | Register a new citizen + seed insurance |
| `GET`  | `/api/admin/citizens` | List all citizens |
| `GET`  | `/api/admin/stats` | Dashboard counters |

### Citizens (`/api/citizens`)

| Method | Path | Role Required | Description |
|--------|------|---------------|-------------|
| `GET`  | `/api/citizens/me` | Any authenticated | Own citizen profile |
| `GET`  | `/api/citizens/{health_id}` | Any hospital | Fetch citizen by Health-ID |
| `PUT`  | `/api/citizens/vitals` | `GOV_APPROVED_HOSPITAL` | Update height/weight/allergies etc. |
| `POST` | `/api/citizens/checkup` | `GOV_APPROVED_HOSPITAL` | Submit periodic checkup (3-5 mo cert) |
| `POST` | `/api/citizens/visits` | Any hospital | Log a medical visit |
| `GET`  | `/api/citizens/visits/{health_id}` | Any hospital | Visit history |

### Insurance (`/api/insurance`)

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/insurance/{health_id}` | All policies for a citizen |
| `GET`  | `/api/insurance/policy/{id}` | Single policy detail |
| `POST` | `/api/insurance/claim` | File a claim (hospital only) |
| `GET`  | `/api/insurance/claims/{health_id}` | Claim history |

### Public (`/api/public`) — **no auth required**

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/public/verify/{health_id}` | Verify Health-ID (for emergency rooms) |

---

## 🧱 Database Schema

```
hospitals          – registered hospitals (approved/pending/rejected)
users              – admin, hospital staff, citizens (auth + roles)
citizens           – core health card (vitals, allergies, blood group, etc.)
checkup_records    – 3-5 month periodic certifications by gov hospitals
medical_visits     – visit logs (diagnosis, prescription, follow-up)
insurance_policies – PM-JAY / private coverage (sum insured, balance)
insurance_claims   – filed claims with balance deduction audit trail
hospital_access_logs – full audit trail of who accessed what
```

---

## 🔐 Security Notes

- All passwords are **bcrypt-hashed** (via passlib)
- JWT tokens expire in 7 days (configurable via `JWT_EXPIRES_IN`)
- Every citizen record access is logged in `hospital_access_logs`
- Neon requires **SSL** (`?sslmode=require`) – enforced in the URL

---

## 📝 Demo Credentials (after seeding)

| Username | Password | Role |
|----------|----------|------|
| `admin` | `Admin@123` | ADMIN |
| `govhospital` | `Hospital@123` | GOV_APPROVED_HOSPITAL |
| `stdhospital` | `Hospital@123` | STANDARD_HOSPITAL |
