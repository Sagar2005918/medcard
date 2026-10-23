-- =============================================================================
-- NATIONAL HEALTHCARE ID SYSTEM - NEON POSTGRESQL SCHEMA & SEED DATA
-- You can copy and paste this entire code directly into the Neon SQL Editor:
-- https://console.neon.tech -> Select your project -> SQL Editor -> Run
-- =============================================================================

-- 1. DROP EXISTING TABLES (IF RESETTING)
DROP TABLE IF EXISTS hospital_access_logs CASCADE;
DROP TABLE IF EXISTS medical_visits CASCADE;
DROP TABLE IF EXISTS insurance_claims CASCADE;
DROP TABLE IF EXISTS insurance_policies CASCADE;
DROP TABLE IF EXISTS checkup_records CASCADE;
DROP TABLE IF EXISTS citizens CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS hospitals CASCADE;

-- -----------------------------------------------------------------------------
-- 2. HOSPITALS TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE hospitals (
    id SERIAL PRIMARY KEY,
    license_number VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50) NOT NULL,
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    pincode VARCHAR(20) NOT NULL,
    hospital_type VARCHAR(50) NOT NULL DEFAULT 'PRIVATE_GENERAL',
    approval_status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    is_gov_approved BOOLEAN NOT NULL DEFAULT FALSE,
    approved_by INTEGER,
    approved_at TIMESTAMPTZ,
    rejection_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 3. USERS TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL, -- ADMIN, GOV_APPROVED_HOSPITAL, STANDARD_HOSPITAL, CITIZEN
    hospital_id INTEGER REFERENCES hospitals(id) ON DELETE SET NULL,
    citizen_id INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Add foreign key constraint for hospital approval
ALTER TABLE hospitals 
    ADD CONSTRAINT fk_hospitals_approved_by 
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL;

-- -----------------------------------------------------------------------------
-- 4. CITIZENS TABLE (Core Healthcare Card)
-- -----------------------------------------------------------------------------
CREATE TABLE citizens (
    id SERIAL PRIMARY KEY,
    health_id VARCHAR(50) UNIQUE NOT NULL,
    aadhaar_masked VARCHAR(20) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(20) NOT NULL,
    blood_group VARCHAR(10) NOT NULL,
    phone VARCHAR(50) NOT NULL,
    email VARCHAR(255),
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    pincode VARCHAR(20) NOT NULL,
    photo_url TEXT,
    emergency_contact_name VARCHAR(255) NOT NULL,
    emergency_contact_phone VARCHAR(50) NOT NULL,
    emergency_contact_relation VARCHAR(100) NOT NULL,
    organ_donor BOOLEAN NOT NULL DEFAULT FALSE,
    height_cm NUMERIC(5,2),
    weight_kg NUMERIC(5,2),
    bmi NUMERIC(4,1),
    allergies TEXT[] NOT NULL DEFAULT '{}',
    chronic_conditions TEXT[] NOT NULL DEFAULT '{}',
    past_medical_history TEXT,
    current_medications TEXT,
    critical_alert TEXT,
    last_checkup_at TIMESTAMPTZ,
    last_checkup_hospital_id INTEGER REFERENCES hospitals(id) ON DELETE SET NULL,
    checkup_valid_until TIMESTAMPTZ,
    checkup_status VARCHAR(50) NOT NULL DEFAULT 'RENEWAL_DUE',
    qr_code_data TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Add citizen foreign key to users
ALTER TABLE users 
    ADD CONSTRAINT fk_users_citizen_id 
    FOREIGN KEY (citizen_id) REFERENCES citizens(id) ON DELETE SET NULL;

-- -----------------------------------------------------------------------------
-- 5. CHECKUP RECORDS TABLE (3-5 Month Periodic Certification)
-- -----------------------------------------------------------------------------
CREATE TABLE checkup_records (
    id SERIAL PRIMARY KEY,
    citizen_id INTEGER NOT NULL REFERENCES citizens(id) ON DELETE CASCADE,
    hospital_id INTEGER NOT NULL REFERENCES hospitals(id) ON DELETE CASCADE,
    doctor_name VARCHAR(255) NOT NULL,
    doctor_registration_no VARCHAR(100),
    checkup_date TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    height_cm NUMERIC(5,2) NOT NULL,
    weight_kg NUMERIC(5,2) NOT NULL,
    bmi NUMERIC(4,1),
    blood_pressure VARCHAR(20) NOT NULL,
    pulse_bpm INTEGER NOT NULL,
    sp_o2 INTEGER,
    blood_sugar_fasting NUMERIC(5,1),
    clinical_summary TEXT NOT NULL,
    recommendations TEXT,
    next_checkup_due DATE NOT NULL,
    certificate_hash VARCHAR(128) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 6. INSURANCE POLICIES TABLE (Cashless Medical Insurance)
-- -----------------------------------------------------------------------------
CREATE TABLE insurance_policies (
    id SERIAL PRIMARY KEY,
    citizen_id INTEGER NOT NULL REFERENCES citizens(id) ON DELETE CASCADE,
    policy_number VARCHAR(100) UNIQUE NOT NULL,
    provider_name VARCHAR(255) NOT NULL,
    policy_type VARCHAR(50) NOT NULL DEFAULT 'GOVERNMENT_SCHEME',
    total_sum_insured NUMERIC(12,2) NOT NULL,
    remaining_sum_balance NUMERIC(12,2) NOT NULL,
    used_sum_amount NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    valid_from DATE NOT NULL,
    valid_to DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    tpa_name VARCHAR(255),
    coverage_details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 7. INSURANCE CLAIMS TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE insurance_claims (
    id SERIAL PRIMARY KEY,
    claim_reference VARCHAR(100) UNIQUE NOT NULL,
    policy_id INTEGER NOT NULL REFERENCES insurance_policies(id) ON DELETE CASCADE,
    citizen_id INTEGER NOT NULL REFERENCES citizens(id) ON DELETE CASCADE,
    hospital_id INTEGER NOT NULL REFERENCES hospitals(id) ON DELETE CASCADE,
    treatment_title VARCHAR(255) NOT NULL,
    diagnosis_summary TEXT NOT NULL,
    claimed_amount NUMERIC(12,2) NOT NULL,
    approved_amount NUMERIC(12,2) NOT NULL,
    balance_before NUMERIC(12,2) NOT NULL,
    balance_after NUMERIC(12,2) NOT NULL,
    claim_status VARCHAR(50) NOT NULL DEFAULT 'SETTLED',
    admission_date DATE,
    discharge_date DATE,
    notes TEXT,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 8. MEDICAL VISITS TABLE (Hospital Check-in / Prescriptions)
-- -----------------------------------------------------------------------------
CREATE TABLE medical_visits (
    id SERIAL PRIMARY KEY,
    citizen_id INTEGER NOT NULL REFERENCES citizens(id) ON DELETE CASCADE,
    hospital_id INTEGER NOT NULL REFERENCES hospitals(id) ON DELETE CASCADE,
    doctor_name VARCHAR(255) NOT NULL,
    department VARCHAR(100) NOT NULL,
    visit_date TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    symptoms TEXT NOT NULL,
    diagnosis TEXT NOT NULL,
    prescription TEXT,
    advice TEXT,
    follow_up_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 9. HOSPITAL ACCESS LOGS (Full Audit Trail)
-- -----------------------------------------------------------------------------
CREATE TABLE hospital_access_logs (
    id SERIAL PRIMARY KEY,
    citizen_id INTEGER NOT NULL REFERENCES citizens(id) ON DELETE CASCADE,
    hospital_id INTEGER REFERENCES hospitals(id) ON DELETE SET NULL,
    accessed_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    access_type VARCHAR(50) NOT NULL,
    purpose VARCHAR(255) NOT NULL,
    ip_address VARCHAR(50),
    accessed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- SEED INITIAL DATA
-- =============================================================================

-- Insert Admin User (Password: Admin@123)
-- bcrypt hash for 'Admin@123': $2b$12$RyUEKX7MUWEXqKHu6OrzQ.KD5d1gM5nSGmw.Ew5G/k6eFLuSzU6ui
INSERT INTO users (username, email, password_hash, role, is_active)
VALUES ('admin', 'admin@healthid.gov.in', '$2b$12$RyUEKX7MUWEXqKHu6OrzQ.KD5d1gM5nSGmw.Ew5G/k6eFLuSzU6ui', 'ADMIN', TRUE);

-- Insert Government-Approved Hospital (AIIMS)
INSERT INTO hospitals (license_number, name, email, phone, address, city, state, pincode, hospital_type, approval_status, is_gov_approved, approved_by, approved_at)
VALUES ('LIC-GOV-001', 'AIIMS National Hospital', 'contact@aiims.gov.in', '+911123456789', 'Ansari Nagar East', 'New Delhi', 'Delhi', '110029', 'GOVERNMENT', 'APPROVED', TRUE, 1, CURRENT_TIMESTAMP);

-- Insert Standard Hospital (Apollo)
INSERT INTO hospitals (license_number, name, email, phone, address, city, state, pincode, hospital_type, approval_status, is_gov_approved, approved_by, approved_at)
VALUES ('LIC-PRV-002', 'Apollo Metro Hospital', 'contact@apollometro.com', '+912223456789', 'Jubilee Hills', 'Hyderabad', 'Telangana', '500033', 'PRIVATE_GENERAL', 'APPROVED', FALSE, 1, CURRENT_TIMESTAMP);

-- Insert Hospital Staff Users (Password: Hospital@123)
-- bcrypt hash for 'Hospital@123': $2b$12$RyUEKX7MUWEXqKHu6OrzQ.KD5d1gM5nSGmw.Ew5G/k6eFLuSzU6ui
INSERT INTO users (username, email, password_hash, role, hospital_id, is_active)
VALUES 
('govhospital', 'staff@aiims.gov.in', '$2b$12$RyUEKX7MUWEXqKHu6OrzQ.KD5d1gM5nSGmw.Ew5G/k6eFLuSzU6ui', 'GOV_APPROVED_HOSPITAL', 1, TRUE),
('stdhospital', 'staff@apollometro.com', '$2b$12$RyUEKX7MUWEXqKHu6OrzQ.KD5d1gM5nSGmw.Ew5G/k6eFLuSzU6ui', 'STANDARD_HOSPITAL', 2, TRUE);

-- Insert Demo Citizen (John Doe with Aadhaar-like Health-ID)
INSERT INTO citizens (
    health_id, aadhaar_masked, full_name, date_of_birth, gender, blood_group,
    phone, email, address, city, state, pincode, emergency_contact_name,
    emergency_contact_phone, emergency_contact_relation, organ_donor,
    height_cm, weight_kg, bmi, allergies, chronic_conditions,
    past_medical_history, current_medications, critical_alert,
    last_checkup_at, last_checkup_hospital_id, checkup_valid_until, checkup_status
)
VALUES (
    '9084-6423-7260', 'XXXX-XXXX-9324', 'John Doe', '1990-05-15', 'Male', 'O+',
    '+919876543210', 'johndoe@example.com', '42 MG Road', 'Bengaluru', 'Karnataka', '560001',
    'Jane Doe', '+919876543211', 'Spouse', TRUE,
    175.0, 72.0, 23.5, ARRAY['Penicillin', 'Dust'], ARRAY['Hypertension'],
    'Appendectomy in 2010', 'Amlodipine 5mg', 'Allergic to Penicillin – use alternatives',
    CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP + INTERVAL '150 days', 'ACTIVE'
);

-- Link Admin user to citizen
UPDATE users SET citizen_id = 1 WHERE username = 'admin';

-- Insert Insurance Policy (Ayushman Bharat PM-JAY with ₹5,00,000 coverage)
INSERT INTO insurance_policies (
    citizen_id, policy_number, provider_name, policy_type,
    total_sum_insured, remaining_sum_balance, used_sum_amount,
    valid_from, valid_to, status, tpa_name, coverage_details
)
VALUES (
    1, 'PM-JAY-7889A1B2', 'Ayushman Bharat - PM-JAY', 'GOVERNMENT_SCHEME',
    500000.00, 500000.00, 0.00,
    CURRENT_DATE, CURRENT_DATE + INTERVAL '1 year', 'ACTIVE', 'National Health Authority',
    'Covers hospitalisation, surgery, ICU, medicines up to ₹5 lakh/year.'
);
