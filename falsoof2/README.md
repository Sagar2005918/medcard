# National Healthcare ID System 🚑

> **A unified, Aadhaar‑style healthcare identity platform and web application built with FastAPI, PostgreSQL (Neon), and Docker deployment on Render.**  
> Every citizen has a unique 12-digit Health-ID (`XXXX-XXXX-XXXX`). Government-approved hospitals update baseline vitals and conduct periodic 3–5 month certifications; all hospitals can view records and log visits; citizens can view their health profile and real-time cashless insurance balances.

---

## 🌐 Full Web Application Features

The application serves a complete, modern responsive web UI directly from the root URL (`/`):

1. **🚨 Emergency Rescue Scan (Zero-Auth)**:
   - Instant triage lookup by 12-digit Health-ID.
   - Highlights critical drug allergies (e.g., Penicillin), blood group, organ donor consent, and emergency contact phone links.
2. **🪪 Citizen Digital Health Card**:
   - High-resolution physical smart-card replica with national insignia, photo avatar, chip illustration, and dynamic QR code.
   - Live biometrics (Height, Weight, BMI with gauge, Blood group).
   - Cashless Insurance Wallet (PM-JAY balance meter, coverage breakdown, and claim history).
   - Medical visit timeline with doctor prescriptions.
   - One-click print/download digital ID card.
3. **🏥 Hospital Clinical Desk**:
   - Patient search by Health-ID.
   - **Log Medical Visits**: Record doctor, department, symptoms, diagnosis, prescriptions, and advice.
   - **3–5 Month Vitals Certification (Gov-Approved Hospitals)**: AIIMS/District hospitals conduct examinations, calculate BMI, and issue cryptographic SHA256 digital seals.
   - **Cashless Claim Settlement**: Instant pre-auth deduction from PM-JAY policy with live balance update.
4. **🛡️ Admin Management Center**:
   - System KPIs and counters.
   - Review and approve/reject pending hospital license applications.
   - Enroll new citizens and automatically assign ₹5,00,000 PM-JAY insurance policies.
   - Citizen directory.
5. **⚡ 1-Click Demo Login & Auto-Seed**:
   - Pre-configured demo accounts in the navigation bar for instant testing (`admin`, `govhospital`, `stdhospital`, and John Doe citizen).


---

## 🏛️ Roles & Access Control

| Role | Permissions |
|------|-------------|
| **`ADMIN`** | Approves/rejects hospitals, registers citizens + seeds insurance, views system stats and audit logs |
| **`GOV_APPROVED_HOSPITAL`** | Updates citizen vitals (height, weight, blood group, allergies) & certifies 3–5 month periodic checkups |
| **`STANDARD_HOSPITAL`** | Reads citizen health cards by Health-ID, logs medical visits & files cashless insurance claims |
| **`CITIZEN`** | Views personal health card profile, vitals, medical visits, and real-time insurance balances |

---

## 🚀 Step-by-Step: Uploading to Neon & Render

### Step 1: Create a Free PostgreSQL Database on Neon

1. Go to [https://neon.tech](https://neon.tech) and sign up / log in.
2. Click **Create Project**.
3. Choose a project name (e.g., `health-id-system`) and select a region closest to you.
4. On the project dashboard, look at the **Connection Details** widget.
5. Select **PostgreSQL** connection string and copy it. It looks like:
   ```
   postgresql://username:password@ep-cool-fog-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
   *(Keep this string handy; you'll supply it to Render and the seed script.)*

---

### Step 2: Push Your Project to GitHub

In your local project root (`/Users/sagarsingh/Desktop/falsoof2`):

```bash
git init
git add .
git commit -m "feat: complete national health id fastapi backend with neon & render config"
```

Create a new repository on [GitHub](https://github.com/new) (e.g., `national-health-id`), then push:

```bash
git remote add origin https://github.com/<your-username>/national-health-id.git
git branch -M main
git push -u origin main
```

---

### Step 3: Deploy on Render

1. Log in to [https://render.com](https://render.com).
2. Click **New +** → **Blueprint** (or **Web Service**):
   - **Option A (Blueprint - Recommended)**:
     - Connect your GitHub repo.
     - Render will automatically read `render.yaml` and configure the Docker runtime and health check (`/health`).
   - **Option B (Manual Web Service)**:
     - Click **New Web Service** and select your GitHub repository.
     - **Runtime**: `Docker`
     - **Dockerfile Path**: `./Dockerfile`
     - **Health Check Path**: `/health`
3. Under **Environment Variables**, set:
   - `DATABASE_URL` = `<Your Neon connection string from Step 1>`
   - `JWT_SECRET` = `any_long_random_secret_key` *(Render can also auto-generate this)*
   - `JWT_EXPIRES_IN` = `7d`
4. Click **Create Web Service** (or **Apply**).
5. Render builds the Docker image and starts the service. Tables will be created automatically on startup!
6. Once deployed, Render will provide a live URL, e.g.:
   `https://national-health-id-system.onrender.com`
7. Visit `https://your-app-name.onrender.com/docs` to test all interactive Swagger endpoints!

---

### Step 4: Seed Initial Demo Data into Neon

Once your Neon database is active, you can populate the demo accounts (Admin, AIIMS Gov Hospital, Apollo Private Hospital, John Doe Citizen with PM-JAY ₹5,00,000 policy) by running the seed script from your machine:

```bash
cd python
DATABASE_URL="<your-neon-connection-string>" python3 seed.py
```

Demo accounts created:
- **Admin**: `admin` / `Admin@123`
- **Gov Hospital**: `govhospital` / `Hospital@123`
- **Standard Hospital**: `stdhospital` / `Hospital@123`
- **Citizen**: John Doe (Health-ID auto-generated during seed)

---

## 💻 Local Testing & Development

1. Install dependencies:
   ```bash
   pip install -r python/requirements.txt
   ```
2. Create/edit `python/.env`:
   ```env
   DATABASE_URL=postgresql://username:password@ep-xxxx.neon.tech/neondb?sslmode=require
   JWT_SECRET=supersecretkey
   JWT_EXPIRES_IN=7d
   ```
3. Run seed:
   ```bash
   cd python && python3 seed.py
   ```
4. Start local server:
   ```bash
   cd python && uvicorn app.main:app --reload --port 8000
   ```
5. Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) in your browser.

---

## 📡 API Overview

- **Auth**: `POST /api/auth/login`, `POST /api/auth/register_hospital`, `GET /api/auth/me`
- **Admin**: `GET /api/admin/hospitals/pending`, `POST /api/admin/hospitals/{id}/approve`, `POST /api/admin/citizens`, `GET /api/admin/stats`
- **Citizens**: `GET /api/citizens/me`, `GET /api/citizens/{health_id}`, `PUT /api/citizens/vitals`, `POST /api/citizens/checkup`, `POST /api/citizens/visits`
- **Insurance**: `GET /api/insurance/{health_id}`, `POST /api/insurance/claim`, `GET /api/insurance/claims/{health_id}`
- **Public**: `GET /api/public/verify/{health_id}` *(No auth required - emergency scan)*
- **Health**: `GET /health`
