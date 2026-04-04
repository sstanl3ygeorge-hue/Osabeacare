# Osabea Healthcare Compliance Portal - Frontend Structure Summary
## For ChatGPT Restructuring

---

## 1. FILE INVENTORY

| File | Lines | Purpose |
|------|-------|---------|
| EmployeeProfilePage.js | 6,926 | Main recruitment/profile page with tabs |
| RecordCheckDialog.js | 1,620 | Multi-step verification dialog for RTW, DBS, Identity, Address |
| UploadRequirementCard.js | 1,477 | Dual-row card (Evidence + Verification) |
| DualRowComplianceSection.js | 756 | Container for compliance sections |
| ReferencesPanel.js | 382 | NEW: References tab content |
| FormCompletionPage.js | 367 | Public form completion with prefill |
| DocumentUploadPage.js | 388 | Public document upload page |
| DocumentRequestsPanel.js | 230 | Request status visibility |
| InterviewFormPanel.js | 294 | Interview records with PDF download |
| AuditTrailPanel.js | 219 | Audit trail timeline |
| RequirementSectionShell.js | 80 | Collapsible section wrapper |
| compliance_index.js | 75 | Export barrel |

---

## 2. CURRENT TAB STRUCTURE (EmployeeProfilePage.js)

```
Tabs: Overview | Compliance | References | Training | Policies | Audit
```

**Tab Triggers (lines 3688-3713):**
```jsx
<TabsList className="bg-white border border-[#E4E8EB] p-1 rounded-xl flex-wrap">
  <TabsTrigger value="overview">Overview</TabsTrigger>
  <TabsTrigger value="checklist">Compliance</TabsTrigger>
  <TabsTrigger value="references">References</TabsTrigger>
  <TabsTrigger value="training">Training</TabsTrigger>
  <TabsTrigger value="policies">Policies</TabsTrigger>
  <TabsTrigger value="audit">Audit</TabsTrigger>
</TabsList>
```

---

## 3. STATE MANAGEMENT (EmployeeProfilePage.js lines 97-200)

```jsx
// Core state
const [employee, setEmployee] = useState(null);
const [documents, setDocuments] = useState([]);
const [policies, setPolicies] = useState([]);
const [training, setTraining] = useState([]);
const [compliance, setCompliance] = useState({});
const [complianceFile, setComplianceFile] = useState(null);
const [complianceRequirements, setComplianceRequirements] = useState({});
const [auditLogs, setAuditLogs] = useState([]);

// Reference state
const [referenceStatus, setReferenceStatus] = useState(null);

// UI state
const [activeTab, setActiveTab] = useState('overview');
const [loading, setLoading] = useState(true);
```

---

## 4. API CALLS / DATA FETCHING

### fetchData() - Initial Load (lines 738-780)
```jsx
const fetchData = async () => {
  const results = await Promise.allSettled([
    axios.get(`${API}/employees/${employeeId}`),
    axios.get(`${API}/employee-documents?employee_id=${employeeId}`),
    axios.get(`${API}/document-types`),
    axios.get(`${API}/policy-assignments?employee_id=${employeeId}`),
    axios.get(`${API}/training-records?employee_id=${employeeId}`),
    axios.get(`${API}/audit-logs?entity_id=${employeeId}&compliance_only=true`),
    axios.get(`${API}/generated-forms?employee_id=${employeeId}`),
    axios.get(`${API}/templates`),
    axios.get(`${API}/employees/${employeeId}/compliance-requirements`)
  ]);
  // Process results...
};
```

### fetchComplianceFile() - Compliance data (lines 793-801)
```jsx
const fetchComplianceFile = async () => {
  const response = await axios.get(`${API}/employees/${employeeId}/compliance-file`);
  setComplianceFile(response.data);
};
```

### fetchReferenceStatus() - References (lines 532-554)
```jsx
const fetchReferenceStatus = async () => {
  const [integrityRes, statusRes] = await Promise.allSettled([
    axios.get(`${API}/references/${employeeId}/integrity`),
    axios.get(`${API}/employees/${employeeId}/references-normalized`)
  ]);
  // Process results...
};
```

---

## 5. KEY COMPONENTS ARCHITECTURE

### UploadRequirementCard - DUAL ROW MODEL
```
┌─────────────────────────────────────────┐
│ Section Header (collapsible)            │
├─────────────────────────────────────────┤
│ ROW A: EVIDENCE                         │
│ - File list with badges                 │
│ - Upload/Request/Manage buttons         │
│ - Verification stamps                   │
├─────────────────────────────────────────┤
│ ROW B: VERIFICATION                     │
│ - Check details (method, outcome, date) │
│ - RTW/DBS/Identity result panels        │
│ - Record Check button                   │
└─────────────────────────────────────────┘
```

### RecordCheckDialog - Multi-step verification
```
Step 1: Select verification method
Step 2: Enter verification details (dates, codes)
Step 3: Record outcome (verified/failed/follow-up)
Step 4: Add notes & submit
```

### ReferencesPanel - Reference workflow
```
┌─────────────────────────────────────────┐
│ Reference 1           │ Reference 2     │
├───────────────────────┼─────────────────┤
│ Declared Info         │ Declared Info   │
│ - Name, Email, Phone  │ - Name, Email   │
│ - Organisation        │ - Organisation  │
├───────────────────────┼─────────────────┤
│ Status Badge          │ Status Badge    │
│ (declared/sent/       │                 │
│  verified)            │                 │
├───────────────────────┼─────────────────┤
│ [Send Request] btn    │ [Send Request]  │
└───────────────────────┴─────────────────┘
```

---

## 6. FORM TEMPLATES RENDERING

Backend defines FORM_TEMPLATES in server.py (lines 4305-4600).
Frontend renders via FormCompletionPage.js:

```jsx
// Fetch form data with auto-fill
useEffect(() => {
  const fetchFormData = async () => {
    const response = await axios.get(`${API}/forms/complete/${token}`);
    setFormData(response.data);
    // auto_fill_data pre-populates fields
    if (response.data.auto_fill_data) {
      setFormValues(response.data.auto_fill_data);
    }
  };
}, [token]);

// Render sections from template
{template?.sections?.map(section => (
  <Card key={section.id}>
    <CardHeader>{section.title}</CardHeader>
    <CardContent>
      {section.fields?.map(field => renderField(field))}
    </CardContent>
  </Card>
))}
```

---

## 7. COMPLIANCE SECTIONS MAPPING

```jsx
// DualRowComplianceSection maps requirement keys to cards:
const COMPLIANCE_SECTIONS = [
  { key: 'right_to_work', label: 'Right to Work', component: UploadRequirementCard },
  { key: 'dbs', label: 'DBS Check', component: UploadRequirementCard },
  { key: 'identity', label: 'Identity', component: UploadRequirementCard },
  { key: 'proof_of_address', label: 'Proof of Address', component: UploadRequirementCard },
  // Additional sections...
];
```

---

## 8. REQUEST-DRIVEN WORKFLOW

Document requests are tracked in `email_requests` collection:

```jsx
// Check request status
const requestState = latestRequest?.status; // pending_send, sent, opened, clicked, submitted

// Display in UI
{latestRequest && (
  <Badge>
    {requestState === 'sent' ? 'Request Sent' :
     requestState === 'opened' ? 'Request Viewed' :
     requestState === 'submitted' ? 'Response Received' : ''}
  </Badge>
)}
```

---

## 9. BACKEND ENDPOINTS USED

| Endpoint | Purpose |
|----------|---------|
| GET /api/employees/{id} | Employee profile |
| GET /api/employees/{id}/compliance-file | Full compliance state |
| GET /api/employees/{id}/compliance-requirements | Requirements + status |
| GET /api/employees/{id}/references | Reference data with declared info |
| GET /api/employees/{id}/references-normalized | Reference verification status |
| GET /api/employees/{id}/document-requests | Request history |
| GET /api/employees/{id}/forms | Form submissions |
| GET /api/employees/{id}/audit-trail | CQC audit trail |
| POST /api/employees/{id}/request-document | Send document request |
| POST /api/employees/{id}/send-reference-request | Send reference request |
| GET /api/forms/complete/{token} | Public form data with auto-fill |
| POST /api/forms/complete/{token} | Submit completed form |

---

## 10. FILES LOCATION

All files are in:
- `/app/frontend/src/pages/portal/EmployeeProfilePage.js`
- `/app/frontend/src/components/compliance/*.js`
- `/app/frontend/src/pages/public/DocumentUploadPage.js`
- `/app/frontend/src/pages/public/FormCompletionPage.js`

Full code export available at: `/app/exports/FRONTEND_CODE_EXPORT.md`

---

## 11. RESTRUCTURING GOALS (Per User Request)

1. **Tab-based navigation** ✓ Already implemented
2. **References display from db.references** ✓ ReferencesPanel.js
3. **Form rendering with prefill** ✓ FormCompletionPage.js
4. **Request-driven workflow visibility** ✓ DocumentRequestsPanel.js
5. **Cleaner CQC-ready UI** - Needs consolidation

## 12. KNOWN ISSUES TO FIX

1. EmployeeProfilePage.js is 6,926 lines - needs splitting
2. Duplicate reference display code in EmployeeProfilePage vs ReferencesPanel
3. Training section still embedded in main page
4. Form system has two entry points (/upload-document and /forms/complete)
