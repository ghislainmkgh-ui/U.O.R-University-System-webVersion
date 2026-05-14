import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./layout/AppShell.jsx";
import { AppNavigationGuard } from "./routes/AppNavigationGuard.jsx";
import { ProtectedRoute } from "./routes/ProtectedRoute.jsx";
import { AccessPage } from "./pages/AccessPage.jsx";
import { AccessRequestsPage } from "./pages/AccessRequestsPage.jsx";
import { AcademicYearsPage } from "./pages/AcademicYearsPage.jsx";
import { AcademicsPage } from "./pages/AcademicsPage.jsx";
import { DashboardPage } from "./pages/DashboardPage.jsx";
import { FinancePage } from "./pages/FinancePage.jsx";
import { LoginPage } from "./pages/LoginPage.jsx";
import { ReportsPage } from "./pages/ReportsPage.jsx";
import { StudentsPage } from "./pages/StudentsPage.jsx";
import { TransfersPage } from "./pages/TransfersPage.jsx";

export function App() {
  const guarded = (page, viewKey) => <AppNavigationGuard viewKey={viewKey}>{page}</AppNavigationGuard>;

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="students" element={guarded(<StudentsPage />, "students")} />
        <Route path="finance" element={guarded(<FinancePage />, "finance")} />
        <Route path="academics" element={guarded(<AcademicsPage />, "academic_data")} />
        <Route path="academic-years" element={guarded(<AcademicYearsPage />, "academic_years")} />
        <Route path="access" element={guarded(<AccessPage />, "access_logs")} />
        <Route path="access-requests" element={guarded(<AccessRequestsPage />, "access_requests")} />
        <Route path="reports" element={guarded(<ReportsPage />, "reports")} />
        <Route path="transfers" element={guarded(<TransfersPage />, "transfers")} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
