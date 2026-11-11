import { Navigate, Route, Routes, useParams } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider, useAuth } from '@/context/AuthContext'
import { AppShell } from '@/components/AppShell'
import { LoadingScreen } from '@/components/ui'
import { LoginPage } from '@/pages/LoginPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { ExpenseCreatePage, ExpenseDetailPage, ExpensesListPage } from '@/pages/ExpensesPages'
import {
  ManagerPaymentsPage,
  PaymentSubmitPage,
  ResidentPaymentsPage,
} from '@/pages/PaymentsPages'
import {
  MaintenanceCreatePage,
  MaintenanceDetailPage,
  MaintenanceListPage,
} from '@/pages/MaintenancePages'
import { AnnouncementsPage } from '@/pages/AnnouncementsPage'
import { NotificationsPage } from '@/pages/NotificationsPage'
import { ReportsPage } from '@/pages/ReportsPage'
import { AuditPage } from '@/pages/AuditPage'
import { ProfilePage } from '@/pages/ProfilePage'
import { BuildingsPage } from '@/pages/BuildingsPage'
import { UnitsPage } from '@/pages/UnitsPage'
import { ResidentsPage } from '@/pages/ResidentsPage'
import { MyApartmentPage, MyExpensesPage } from '@/pages/ResidentPages'
import {
  LandingPage,
  PasswordRecoveryPage,
  PricingPage,
  RegisterPage,
} from '@/pages/PublicPages'
import { OnboardingPage } from '@/pages/OnboardingPages'
import { AcceptInvitePage, InvitationsPage, SubscriptionPage } from '@/pages/SubscriptionPages'
import { SupportDetailPage, SupportListPage } from '@/pages/SupportPages'
import {
  AdminBuildingsPage,
  AdminDashboardPage,
  AdminManagersPage,
  AdminPaymentsPage,
  AdminPlansPage,
  AdminSettingsPage,
  AdminShell,
  AdminSubscriptionsPage,
  AdminSupportPage,
} from '@/pages/AdminPages'

function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingScreen />
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

function InviteRoute() {
  const { token } = useParams()
  return <AcceptInvitePage token={token || ''} />
}

function AppRoutes() {
  const { user, loading, isSuperAdmin } = useAuth()
  if (loading) return <LoadingScreen label="آماده‌سازی سامانه…" />

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/pricing" element={<PricingPage />} />
      <Route path="/register" element={user ? <Navigate to="/onboarding" replace /> : <RegisterPage />} />
      <Route path="/forgot-password" element={<PasswordRecoveryPage />} />
      <Route path="/invite/:token" element={<InviteRoute />} />
      <Route
        path="/login"
        element={
          user ? (
            <Navigate to={isSuperAdmin ? '/admin' : '/app/dashboard'} replace />
          ) : (
            <LoginPage />
          )
        }
      />
      <Route
        path="/onboarding"
        element={
          <Protected>
            <OnboardingPage />
          </Protected>
        }
      />

      <Route
        path="/admin"
        element={
          <Protected>
            <AdminShell />
          </Protected>
        }
      >
        <Route index element={<AdminDashboardPage />} />
        <Route path="buildings" element={<AdminBuildingsPage />} />
        <Route path="managers" element={<AdminManagersPage />} />
        <Route path="plans" element={<AdminPlansPage />} />
        <Route path="payments" element={<AdminPaymentsPage />} />
        <Route path="subscriptions" element={<AdminSubscriptionsPage />} />
        <Route path="support" element={<AdminSupportPage />} />
        <Route path="settings" element={<AdminSettingsPage />} />
      </Route>

      <Route
        path="/app"
        element={
          <Protected>
            <AppShell />
          </Protected>
        }
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="buildings" element={<BuildingsPage />} />
        <Route path="units" element={<UnitsPage />} />
        <Route path="residents" element={<ResidentsPage />} />
        <Route path="invitations" element={<InvitationsPage />} />
        <Route path="expenses" element={<ExpensesListPage />} />
        <Route path="expenses/new" element={<ExpenseCreatePage />} />
        <Route path="expenses/:id" element={<ExpenseDetailPage />} />
        <Route path="payments" element={<ManagerPaymentsPage />} />
        <Route path="payments/submit" element={<PaymentSubmitPage />} />
        <Route path="my-expenses" element={<MyExpensesPage />} />
        <Route path="my-payments" element={<ResidentPaymentsPage />} />
        <Route path="my-apartment" element={<MyApartmentPage />} />
        <Route path="maintenance" element={<MaintenanceListPage />} />
        <Route path="maintenance/new" element={<MaintenanceCreatePage />} />
        <Route path="maintenance/:id" element={<MaintenanceDetailPage />} />
        <Route path="announcements" element={<AnnouncementsPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="audit" element={<AuditPage />} />
        <Route path="subscription" element={<SubscriptionPage />} />
        <Route path="support" element={<SupportListPage />} />
        <Route path="support/:id" element={<SupportDetailPage />} />
        <Route path="profile" element={<ProfilePage />} />
      </Route>
      <Route path="*" element={<Navigate to={user ? '/app/dashboard' : '/'} replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <Toaster
        position="top-center"
        toastOptions={{
          className: 'text-sm',
          style: { fontFamily: 'Vazirmatn, sans-serif' },
        }}
      />
      <AppRoutes />
    </AuthProvider>
  )
}
