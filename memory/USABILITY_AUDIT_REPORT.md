# System Usability Audit Report
## Osabea Healthcare Compliance Portal
### Date: April 5, 2026

---

## Executive Summary

This audit evaluates the system against the **5 E's of Usability**:
1. **Effective** - Can users complete their goals?
2. **Efficient** - Can they do it quickly?
3. **Engaging** - Is it pleasant to use?
4. **Error Tolerant** - Does it handle mistakes gracefully?
5. **Easy to Learn** - Can new users figure it out?

### Overall Score: 72/100

| Criterion | Score | Status |
|-----------|-------|--------|
| Effective | 8/10 | ✅ Good |
| Efficient | 7/10 | 🟡 Needs Work |
| Engaging | 8/10 | ✅ Good |
| Error Tolerant | 6/10 | ❌ Critical Issues |
| Easy to Learn | 7/10 | 🟡 Needs Work |

---

## Page-by-Page Audit

### 1. Public Homepage

#### What Works ✅
- Clean, professional design
- CQC compliance badge prominently displayed
- Clear value proposition for care homes
- Trust indicators (500+ staff, 50+ care homes)
- How It Works 5-step process
- Testimonials section
- Phone number visible (01634 306 000)
- Mobile responsive

#### What Needs Fixing ❌
- None critical

#### Recommendations
- Add real client logos when available
- Add live chat widget for instant support

---

### 2. Admin Dashboard

#### What Works ✅
- Clean layout with sidebar navigation
- Quick access to key sections
- Notification bell visible
- System Admin user display

#### What Needs Fixing ❌
- No actionable task queue visible on first load
- Dashboard could show more compliance metrics at a glance

#### Recommendations
- Add "Today's Tasks" widget showing pending verifications
- Add expiring documents alert banner

---

### 3. Employee Profile Page

#### What Works ✅
- ConsolidatedStatusPanel at top (single source of truth)
- 7-tab navigation (Work Readiness, Compliance, Forms, Training, References, Employment, Audit)
- Progress calculation now correct (17% for 2/12)
- Blocker list with actionable items
- Quick Actions buttons

#### What Needs Fixing ❌
| Issue | Priority | Details |
|-------|----------|---------|
| **No [Edit] buttons on sections** | P0 | Personal details, employment history, references have no edit buttons |
| **Category breakdown shows 0/0 for all** | P1 | Documents 0/5 but grid shows 0/0 |
| **Quick Actions + Tabs redundancy** | P2 | "View References" in Quick Actions and References tab |

#### Recommendations
1. Add [Edit] button to every section header
2. Fix category breakdown to show actual counts
3. Consider removing Quick Actions (tabs provide same navigation)

---

### 4. Compliance Tab

#### What Works ✅
- Progress bar visible (2/12 requirements complete - 17%)
- Category breakdown grid (Documents, Forms, Training, References, Agreements, Induction)
- "10 Blocking Requirements" clearly listed
- "Not Ready to Work" badge visible

#### What Needs Fixing ❌
| Issue | Priority | Details |
|-------|----------|---------|
| **Blocking requirements list hard to scan** | P1 | Needs visual hierarchy (icons, colors) |

#### Recommendations
- Add red/amber/green color coding to blocking items
- Group blocking items by category

---

### 5. Employment Tab

#### What Works ✅
- Employment history displayed
- CV gaps detection working

#### What Needs Fixing ❌
| Issue | Priority | Details |
|-------|----------|---------|
| **No [Edit] button for employment history** | P0 | Admin cannot edit incorrect employment records |
| **No "Mark gap as explained" UI** | P1 | Gap explanations require backend edit |

#### Recommendations
1. Add [Edit] button to Employment History section
2. Add inline "Explain Gap" button for each detected gap

---

### 6. References Tab

#### What Works ✅
- Reference 1 and Reference 2 cards visible
- "Not Declared" status shown
- Reference-Employment Cross Check section
- NHS-level reference verification noted

#### What Needs Fixing ❌
| Issue | Priority | Details |
|-------|----------|---------|
| **No [Edit] button for references** | P0 | Admin cannot edit referee details |
| **Missing NHS-required fields** | P1 | Referee type, period of supervision, direct supervisor, can contact before offer |
| **No "Add Referee Details" from this tab** | P2 | Must go elsewhere to add |

#### Recommendations
1. Add [Edit] button to each reference card
2. Add NHS-required fields to reference form
3. Add "Add Referee Details" button directly on this tab

---

### 7. Worker Dashboard

#### What Works ✅
- Document upload guidance text (now correct)
- Progress tracking
- Forms to complete list
- Documents to upload list

#### What Needs Fixing ❌
| Issue | Priority | Details |
|-------|----------|---------|
| **Guidance text may be cached incorrectly** | P1 | User reported "garbled" text |
| **Contract signing needs worker signature** | P0 | CQC compliance requirement |

#### Recommendations
1. Clear browser cache and verify guidance text
2. Ensure contract signing only available to workers

---

## Critical Issues Summary (P0 - Must Fix Before Launch)

### 1. Universal Editability
**Status: ❌ NOT IMPLEMENTED IN UI**

Backend endpoints created but UI missing:
- `PUT /employees/{id}/personal-details` ✅ Backend exists
- `POST /employees/{id}/employment-history` ✅ Backend exists
- `PUT /employees/{id}/references/{ref_id}` ✅ Backend exists
- `POST /employees/{id}/contract/supersede` ✅ Backend exists

**FIX NEEDED:** Add [Edit] buttons to UI sections that call these endpoints.

### 2. Contract Signing by Worker
**Status: ✅ FIXED**

- Frontend blocks admin from signing contracts ✅
- Backend rejects admin contract signing ✅
- Supersede endpoint available ✅

### 3. Category Breakdown Grid
**Status: ❌ SHOWING 0/0**

The category breakdown shows Documents 0/0, Forms 0/0, etc. but should show actual counts.

**FIX NEEDED:** Debug category breakdown data source.

---

## P1 Issues (Should Fix Before Launch)

| Issue | Page | Fix Required |
|-------|------|--------------|
| Employment History Edit UI | Employment Tab | Add [Edit] button + EditEmploymentHistoryDialog |
| Reference Edit UI | References Tab | Add [Edit] button + EditReferenceDialog |
| Personal Details Edit UI | Profile Header | Add [Edit] button + EditPersonalDetailsDialog |
| NHS Reference Fields | Add Reference Form | Add referee_type, period_of_supervision, is_direct_supervisor, can_contact_before_offer |
| Gap Explanation UI | Employment Tab | Add inline "Explain Gap" button |

---

## P2 Issues (Nice to Have)

| Issue | Page | Fix Required |
|-------|------|--------------|
| Quick Actions redundancy | Employee Profile | Consider removing (tabs do same job) |
| Bulk Import UI | Admin Dashboard | Add UI for CSV import |
| PDF Application Import | Admin Dashboard | Add AI extraction for existing PDF forms |

---

## Implementation Checklist

### P0 (Do Now - Blocking Launch)
- [ ] Add [Edit] button to Personal Details section
- [ ] Add [Edit] button to Employment History section
- [ ] Add [Edit] button to References section
- [ ] Fix category breakdown to show actual counts
- [ ] Test contract signing flow (worker only)

### P1 (Do Before Launch)
- [ ] Add NHS-required fields to referee form
- [ ] Add inline gap explanation button
- [ ] Add [Supersede Contract] button for admin-signed contracts
- [ ] Verify worker dashboard guidance text

### P2 (Post-Launch)
- [ ] Add bulk import UI
- [ ] Add PDF AI extraction
- [ ] Refactor server.py (>50k lines)

---

## Files to Modify

### Frontend
1. `/app/frontend/src/pages/portal/EmployeeProfilePage.js`
   - Add [Edit] buttons to sections
   - Import edit dialogs
   - Wire up dialog open/close

2. `/app/frontend/src/components/compliance/ConsolidatedStatusPanel.js`
   - Fix category breakdown data binding

### Backend
All edit endpoints already exist:
- `/api/employees/{id}/personal-details` (PUT)
- `/api/employees/{id}/employment-history` (POST)
- `/api/employees/{id}/references/{ref_id}` (PUT)
- `/api/employees/{id}/contract/supersede` (POST)

---

## Test Scenarios

### Before Launch
1. ✅ Login as admin
2. ✅ Navigate to employee profile
3. ❌ Edit personal details (no UI)
4. ❌ Edit employment history (no UI)
5. ❌ Edit reference (no UI)
6. ✅ Try to sign contract as admin (should be blocked)
7. ❌ Supersede contract (no UI)
8. ❌ Verify category breakdown shows correct counts

---

## Conclusion

The system has a **solid foundation** but needs **UI integration** of the edit functionality before launch. The backend is ready - the edit endpoints with reason logging are implemented. The critical gap is adding [Edit] buttons to the frontend that call these endpoints.

**Estimated effort to complete P0:** 2-4 hours
**Estimated effort to complete P1:** 4-8 hours

---

*Audit conducted by Emergent AI Agent*
*April 5, 2026*
