import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";

// Public Pages
import HomePage from "./pages/public/HomePage";
import AboutPage from "./pages/public/AboutPage";
import ServicesPage from "./pages/public/ServicesPage";
import PublicRecruitmentPage from "./pages/public/RecruitmentPage";
import CompliancePage from "./pages/public/CompliancePage";
import ContactPage from "./pages/public/ContactPage";
import ApplyPage from "./pages/public/ApplyPage";
import FormCompletionPage from "./pages/public/FormCompletionPage";
import RefereeCompletionPage from "./pages/public/RefereeCompletionPage";
import TrainingUploadPage from "./pages/public/TrainingUploadPage";
import DocumentUploadPage from "./pages/public/DocumentUploadPage";

// Auth Pages
import LoginPage from "./pages/auth/LoginPage";
import AuthCallback from "./pages/auth/AuthCallback";

// Worker Portal Pages
import WorkerLoginPage from "./pages/worker/WorkerLoginPage";
import WorkerVerifyPage from "./pages/worker/WorkerVerifyPage";
import WorkerDashboard from "./pages/worker/WorkerDashboard";
import WorkerFormPage from "./pages/worker/WorkerFormPage";

// Portal Pages
import PortalLayout from "./components/portal/PortalLayout";
import DashboardPage from "./pages/portal/DashboardPage";
import EmployeesPage from "./pages/portal/EmployeesPage";
import EmployeeProfilePage from "./pages/portal/EmployeeProfilePage";
import DocumentsPage from "./pages/portal/DocumentsPage";
// PoliciesPage removed - policy management consolidated in Compliance Centre
// import PoliciesPage from "./pages/portal/PoliciesPage";
// DocumentsPage kept for backward compatibility but route disabled
import TrainingPage from "./pages/portal/TrainingPage";
import AuditViewPage from "./pages/portal/AuditViewPage";
import DBSRegisterPage from "./pages/portal/DBSRegisterPage";
import SettingsPage from "./pages/portal/SettingsPage";
import TemplatesPage from "./pages/portal/TemplatesPage";
import BulkImportPage from "./pages/portal/BulkImportPage";
import FormEditorPage from "./pages/portal/FormEditorPage";
import ComplianceCentrePage from "./pages/portal/ComplianceCentrePage";
import ServiceUsersPage from "./pages/portal/ServiceUsersPage";
import ServiceUserProfilePage from "./pages/portal/ServiceUserProfilePage";
import RecruitmentPipelinePage from "./pages/portal/RecruitmentPage";
import ScheduledRequestsPage from "./pages/portal/ScheduledRequestsPage";
import AdminUsersPage from "./pages/portal/AdminUsersPage";

// Auth Context
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/auth/ProtectedRoute";

function AppRouter() {
  const location = useLocation();
  
  // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
  // Check URL fragment for session_id during render (NOT in useEffect)
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }

  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<HomePage />} />
      <Route path="/about" element={<AboutPage />} />
      <Route path="/services" element={<ServicesPage />} />
      <Route path="/recruitment" element={<PublicRecruitmentPage />} />
      <Route path="/compliance" element={<CompliancePage />} />
      <Route path="/contact" element={<ContactPage />} />
      <Route path="/apply" element={<ApplyPage />} />
      
      {/* Public Form Completion Route (No Auth Required) */}
      <Route path="/forms/complete/:token" element={<FormCompletionPage />} />
      
      {/* Public Referee Reference Completion Route (No Auth Required) */}
      <Route path="/referee/complete/:token" element={<RefereeCompletionPage />} />
      
      {/* Public Training Certificate Upload Route (No Auth Required) */}
      <Route path="/training/upload/:token" element={<TrainingUploadPage />} />
      
      {/* Public Document Upload Route (No Auth Required - From Email Links) */}
      <Route path="/upload-document" element={<DocumentUploadPage />} />
      
      {/* Auth Routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      
      {/* Worker Portal Routes (No Admin Auth Required) */}
      <Route path="/worker/login" element={<WorkerLoginPage />} />
      <Route path="/worker/verify" element={<WorkerVerifyPage />} />
      <Route path="/worker/dashboard" element={<WorkerDashboard />} />
      <Route path="/worker/forms/:formId" element={<WorkerFormPage />} />
      
      {/* Portal Routes - Protected */}
      <Route path="/portal" element={
        <ProtectedRoute>
          <PortalLayout />
        </ProtectedRoute>
      }>
        <Route index element={<DashboardPage />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="employees" element={<EmployeesPage />} />
        <Route path="employees/:employeeId" element={<EmployeeProfilePage />} />
        <Route path="recruitment" element={<RecruitmentPipelinePage />} />
        <Route path="recruitment/:employeeId" element={<EmployeeProfilePage />} />
        <Route path="bulk-import" element={<BulkImportPage />} />
        {/* Documents route removed - all document management is now per-employee in Employee Profile → Documents tab */}
        {/* <Route path="documents" element={<DocumentsPage />} /> */}
        {/* Policies route removed - policy management consolidated in Compliance Centre */}
        {/* <Route path="policies" element={<PoliciesPage />} /> */}
        <Route path="training" element={<TrainingPage />} />
        <Route path="dbs-register" element={<DBSRegisterPage />} />
        <Route path="templates" element={<TemplatesPage />} />
        <Route path="compliance-centre" element={<ComplianceCentrePage />} />
        <Route path="forms/:formId" element={<FormEditorPage />} />
        <Route path="audit" element={<AuditViewPage />} />
        <Route path="service-users" element={<ServiceUsersPage />} />
        <Route path="service-users/:id" element={<ServiceUserProfilePage />} />
        <Route path="scheduled-requests" element={<ScheduledRequestsPage />} />
        <Route path="admin-users" element={<AdminUsersPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRouter />
        <Toaster position="top-right" richColors />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
