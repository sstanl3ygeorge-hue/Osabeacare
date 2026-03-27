import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";

// Public Pages
import HomePage from "./pages/public/HomePage";
import AboutPage from "./pages/public/AboutPage";
import ServicesPage from "./pages/public/ServicesPage";
import RecruitmentPage from "./pages/public/RecruitmentPage";
import CompliancePage from "./pages/public/CompliancePage";
import ContactPage from "./pages/public/ContactPage";
import ApplyPage from "./pages/public/ApplyPage";

// Auth Pages
import LoginPage from "./pages/auth/LoginPage";
import AuthCallback from "./pages/auth/AuthCallback";

// Portal Pages
import PortalLayout from "./components/portal/PortalLayout";
import DashboardPage from "./pages/portal/DashboardPage";
import EmployeesPage from "./pages/portal/EmployeesPage";
import EmployeeProfilePage from "./pages/portal/EmployeeProfilePage";
import DocumentsPage from "./pages/portal/DocumentsPage";
import PoliciesPage from "./pages/portal/PoliciesPage";
import TrainingPage from "./pages/portal/TrainingPage";
import AuditViewPage from "./pages/portal/AuditViewPage";
import SettingsPage from "./pages/portal/SettingsPage";
import TemplatesPage from "./pages/portal/TemplatesPage";
import FormEditorPage from "./pages/portal/FormEditorPage";
import ComplianceCentrePage from "./pages/portal/ComplianceCentrePage";

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
      <Route path="/recruitment" element={<RecruitmentPage />} />
      <Route path="/compliance" element={<CompliancePage />} />
      <Route path="/contact" element={<ContactPage />} />
      <Route path="/apply" element={<ApplyPage />} />
      
      {/* Auth Routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      
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
        <Route path="documents" element={<DocumentsPage />} />
        <Route path="policies" element={<PoliciesPage />} />
        <Route path="training" element={<TrainingPage />} />
        <Route path="templates" element={<TemplatesPage />} />
        <Route path="compliance-centre" element={<ComplianceCentrePage />} />
        <Route path="forms/:formId" element={<FormEditorPage />} />
        <Route path="audit" element={<AuditViewPage />} />
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
