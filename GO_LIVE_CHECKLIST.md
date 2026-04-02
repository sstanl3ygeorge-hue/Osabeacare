# PRODUCTION GO-LIVE CHECKLIST
## Osabeacare Compliance Portal

**Date:** 2026-04-02  
**Status:** READY FOR PRODUCTION

---

## ✅ Pre-Go-Live Verification Complete

| Check | Status | Notes |
|-------|--------|-------|
| Backend API | ✅ Online | api.osabeacares.co.uk |
| Frontend App | ✅ Online | app.osabeacares.co.uk |
| Database | ✅ Connected | Railway MongoDB |
| Admin User | ✅ Created | admin@osabea.care |
| Training Catalogue | ✅ Seeded | 7 items |
| Employee Creation | ✅ Tested | Works from empty state |
| Compliance Engine | ✅ Tested | Correctly shows all blockers |
| Work Readiness | ✅ Tested | 3-tier status working |
| Training Engine | ✅ Tested | Shows required items |

---

## 🚀 GO-LIVE STEPS

### Step 1: First Login
1. Open: https://app.osabeacares.co.uk
2. Login: `admin@osabea.care` / `admin123`
3. **Immediately change admin password** via Profile

### Step 2: Create Additional Admin Users (if needed)
1. Go to Settings > Users
2. Create accounts for other administrators
3. Assign appropriate roles

### Step 3: Begin Onboarding First Employee
1. Go to **Recruitment** > **New Applicant**
2. Fill in:
   - First Name, Last Name
   - Email, Phone
   - Role (e.g., care_assistant, registered_nurse)
3. Submit to create applicant record

### Step 4: Compliance Workflow
For each applicant, complete:

**Documents:**
- [ ] Upload CV
- [ ] Upload ID documents
- [ ] Upload proof of address (x2)
- [ ] Upload DBS certificate
- [ ] Upload Right to Work documents

**Verification Checks:**
- [ ] Record RTW check (with proof)
- [ ] Record DBS check (with proof)
- [ ] Record Identity verification (with proof)
- [ ] Record Address verification (with proof)

**References:**
- [ ] Add Reference 1 details
- [ ] Add Reference 2 details
- [ ] Send reference requests
- [ ] Record reference responses

**Training:**
- [ ] Upload mandatory training certificates
- [ ] Verify training completion dates

**Agreements:**
- [ ] Contract acceptance
- [ ] Handbook acknowledgement

### Step 5: Approve Recruitment
Once all blockers cleared:
1. Review compliance file
2. Check Work Readiness shows "Ready" or "Ready with Conditions"
3. Click "Approve Recruitment"
4. Employee moves to onboarding/active status

---

## 📋 DAILY OPERATIONS CHECKLIST

### New Applicants
- [ ] Create applicant record
- [ ] Send reference requests
- [ ] Begin document collection

### Compliance Monitoring
- [ ] Check expiring documents
- [ ] Review pending reference requests
- [ ] Update training records

### Work Readiness
- [ ] Review "Not Ready" employees
- [ ] Clear blockers
- [ ] Approve ready employees

---

## 🔐 SECURITY REMINDERS

1. **Change default admin password immediately**
2. **Use strong passwords** for all accounts
3. **HTTPS only** - all traffic encrypted
4. **Regular backups** - Railway handles this

---

## 📞 SUPPORT

- **Technical Issues:** Check Railway dashboard for logs
- **Feature Questions:** Review compliance workflow documentation
- **Data Issues:** Contact development team

---

## 🎯 SUCCESS METRICS

After first week:
- [ ] At least 1 employee fully onboarded
- [ ] All compliance checks working
- [ ] No critical errors in logs

After first month:
- [ ] Regular onboarding workflow established
- [ ] Expiry monitoring active
- [ ] Reference workflow tested end-to-end
