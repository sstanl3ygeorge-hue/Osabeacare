# Supabase Staging Setup Guide

## 1. CREATE SUPABASE PROJECT

### Step 1.1: Create Project
1. Go to: https://supabase.com/dashboard
2. Click **"New Project"**
3. Fill in:
   - **Name**: `osabeacare-staging`
   - **Database Password**: Generate strong password (SAVE THIS)
   - **Region**: `eu-west-2` (London) - closest to UK users
4. Click **"Create new project"**
5. Wait ~2 minutes for provisioning

### Step 1.2: Get Connection Details
After project is ready, go to **Settings** → **Database**:

```
Host: db.<project-ref>.supabase.co
Database: postgres
Port: 5432
User: postgres
Password: <your-database-password>
```

**Connection String (save this):**
```
postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
```

### Step 1.3: Get API Keys
Go to **Settings** → **API**:
- `SUPABASE_URL`: https://<project-ref>.supabase.co
- `SUPABASE_ANON_KEY`: (public, safe for frontend)
- `SUPABASE_SERVICE_KEY`: (secret, backend only)

---

## 2. BACKEND ENVIRONMENT VARIABLES

Add these to Railway **Variables** tab:

```bash
# Existing MongoDB (keep for fallback)
MONGO_URL=${{MongoDB.MONGO_URL}}
DB_NAME=osabeacare_prod

# Supabase Connection
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_KEY=<anon-key>
SUPABASE_SERVICE_KEY=<service-role-key>
SUPABASE_DB_URL=postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres

# Feature Flags (start with mongo, switch gradually)
READ_SOURCE_EMPLOYEES=mongo
READ_SOURCE_COMPLIANCE=mongo
READ_SOURCE_TRAINING=mongo
READ_SOURCE_DOCUMENTS=mongo

# Existing vars (keep as-is)
JWT_SECRET=osabea-care-jwt-secret-2024-secure
CORS_ORIGINS=https://app.osabeacares.co.uk
RESEND_API_KEY=re_GZMwWjMJ_BCtwKwXMeqH3hcvcTP1XK9qf
SENDER_EMAIL=Osabea Recruitment Team <recruitment@osabeacares.co.uk>
REPLY_TO_EMAIL=info@osabeacaresolutions.co.uk
ADMIN_EMAIL=admin@osabea.care
EMERGENT_LLM_KEY=sk-emergent-990C21c55Ba62Ac672
```

---

## 3. SCHEMA DEPLOYMENT

### Step 3.1: Open SQL Editor
In Supabase dashboard: **SQL Editor** → **New Query**

### Step 3.2: Run Schema
Copy contents of `/app/migration/sql/schema/001_create_schema.sql` and execute.

**Or via CLI:**
```bash
# Install Supabase CLI
npm install -g supabase

# Login
supabase login

# Link project
supabase link --project-ref <your-project-ref>

# Run migration
psql "postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres" -f /app/migration/sql/schema/001_create_schema.sql
```

### Step 3.3: Verify Tables
Run in SQL Editor:
```sql
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
```

**Expected tables:**
- profiles
- employees
- documents
- rtw_checks
- dbs_checks
- identity_checks
- address_checks
- training_catalogue
- training_records
- form_templates
- form_submissions
- agreement_templates
- agreement_acknowledgements
- org_policies
- org_certificates
- audit_logs
- migration_state

---

## 4. STORAGE BUCKET SETUP

### Step 4.1: Create Buckets
In Supabase dashboard: **Storage** → **New Bucket**

Create these buckets:

| Bucket Name | Public | Purpose |
|-------------|--------|---------|
| `documents` | No | Employee documents (private) |
| `proof-files` | No | Verification proof files |
| `profile-photos` | Yes | Employee profile photos |
| `org-files` | No | Policies, certificates |

### Step 4.2: Set Bucket Policies
For `documents` bucket (private, authenticated access):
```sql
-- In SQL Editor
CREATE POLICY "Authenticated users can upload documents"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'documents');

CREATE POLICY "Authenticated users can view documents"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'documents');
```

For `profile-photos` bucket (public read):
```sql
CREATE POLICY "Anyone can view profile photos"
ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'profile-photos');

CREATE POLICY "Authenticated users can upload profile photos"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'profile-photos');
```

---

## 5. DATA MIGRATION

### Step 5.1: Run Migration Scripts
On your local machine or Emergent pod:

```bash
cd /app/migration

# Set environment variables
export MONGO_URL="mongodb://localhost:27017"
export DB_NAME="test_database"
export SUPABASE_DB_URL="postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres"

# Dry run first
python run_migration.py --dry-run

# If dry run passes, run actual migration
python run_migration.py
```

### Step 5.2: Validate Migration
```bash
python run_validation.py
```

Or run SQL:
```sql
-- Check record counts
SELECT 'profiles' as table_name, COUNT(*) as count FROM profiles
UNION ALL SELECT 'employees', COUNT(*) FROM employees
UNION ALL SELECT 'documents', COUNT(*) FROM documents
UNION ALL SELECT 'training_records', COUNT(*) FROM training_records
UNION ALL SELECT 'audit_logs', COUNT(*) FROM audit_logs;
```

---

## 6. FIRST READ-SWITCH TEST PLAN

### Step 6.1: Pre-Switch Checklist
- [ ] Schema deployed successfully
- [ ] All tables created
- [ ] Migration completed
- [ ] Record counts match MongoDB
- [ ] Storage buckets created

### Step 6.2: Enable First Read (Employees List)
In Railway, update variable:
```
READ_SOURCE_EMPLOYEES=supabase
```
Redeploy backend.

### Step 6.3: Test Endpoints
```bash
API_URL="https://api.osabeacares.co.uk"

# Login
TOKEN=$(curl -s -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@osabea.care","password":"admin123"}' | \
  python3 -c "import sys,json;print(json.load(sys.stdin).get('token',''))")

# Test employees list
curl -s "$API_URL/api/employees" -H "Authorization: Bearer $TOKEN" | \
  python3 -c "import sys,json;d=json.load(sys.stdin);print(f'Count: {len(d)}')"

# Check source status
curl -s "$API_URL/api/admin/read-source-status" -H "Authorization: Bearer $TOKEN"
```

### Step 6.4: Check Logs
In Railway dashboard, view **Deploy Logs** for:
```
[SOURCE:EMPLOYEES] GET /employees -> SUPABASE (records=12, latency=45ms)
```

### Step 6.5: Rollback if Needed
If issues occur:
```
READ_SOURCE_EMPLOYEES=mongo
```
Redeploy.

---

## 7. GRADUAL ROLLOUT SEQUENCE

| Day | Action | Flag Change |
|-----|--------|-------------|
| 1 | Enable employees read | `READ_SOURCE_EMPLOYEES=supabase` |
| 2 | Monitor, verify | - |
| 3 | Enable compliance read | `READ_SOURCE_COMPLIANCE=supabase` |
| 4 | Monitor, verify | - |
| 5 | Enable training read | `READ_SOURCE_TRAINING=supabase` |
| 6 | Enable documents read | `READ_SOURCE_DOCUMENTS=supabase` |
| 7 | Full validation | All flags = supabase |

---

## QUICK REFERENCE

### Supabase Dashboard URLs
- Project: `https://supabase.com/dashboard/project/<project-ref>`
- SQL Editor: `https://supabase.com/dashboard/project/<project-ref>/sql`
- Storage: `https://supabase.com/dashboard/project/<project-ref>/storage`
- Settings: `https://supabase.com/dashboard/project/<project-ref>/settings`

### Connection Test
```bash
psql "postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres" -c "SELECT 1"
```

### Emergency Rollback
```bash
# Set all flags back to mongo in Railway
READ_SOURCE_EMPLOYEES=mongo
READ_SOURCE_COMPLIANCE=mongo
READ_SOURCE_TRAINING=mongo
READ_SOURCE_DOCUMENTS=mongo
```
