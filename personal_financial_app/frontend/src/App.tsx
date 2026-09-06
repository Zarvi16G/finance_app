/**
 * Application entry component: auth provider + client-side router.
 *
 * Routes are named in Spanish, matching the navigation. The two English
 * paths that shipped earlier (/statements, /debts, …) are kept as redirects
 * rather than dropped, so a bookmark or a link from an older session still
 * lands somewhere.
 *
 * The second-factor step sits under PublicOnlyRoute alongside login: at that
 * point the visitor has cleared the password but holds no session, so it is
 * a public page by definition.
 */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { ProtectedRoute, PublicOnlyRoute } from './auth/ProtectedRoute';
import FullLayout from './layouts/FullLayout';
import Login from './pages/Login';
import TwoFactorChallenge from './pages/TwoFactorChallenge';
import Register from './pages/Register';
import Dashboard from './components/dashboard/Dashboard';
import AnalyticsDashboard from './components/analytics/AnalyticsDashboard';
import StatementList from './components/statements/StatementList';
import StatementUploader from './components/statements/StatementUploader';
import StatementReview from './components/statements/StatementReview';
import DebtRegistry from './components/debts/DebtRegistry';
import DebtDetail from './components/debts/DebtDetail';
import GoalsList from './components/goals/GoalsList';
import Experiences from './components/experiences/Experiences';
import Patrimony from './components/patrimony/Patrimony';
import Wealthness from './components/wealthness/Wealthness';
import Analysis from './components/analysis/Analysis';
import ProfileSettings from './components/profile/ProfileSettings';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<PublicOnlyRoute />}>
            <Route path="/login" element={<Login />} />
            <Route path="/login/2fa" element={<TwoFactorChallenge />} />
            <Route path="/register" element={<Register />} />
          </Route>

          <Route element={<ProtectedRoute />}>
            <Route element={<FullLayout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/movimientos" element={<AnalyticsDashboard />} />
              <Route path="/extractos" element={<StatementList />} />
              <Route path="/extractos/subir" element={<StatementUploader />} />
              <Route path="/extractos/:id/revisar" element={<StatementReview />} />
              <Route path="/deudas" element={<DebtRegistry />} />
              <Route path="/deudas/:id" element={<DebtDetail />} />
              <Route path="/metas" element={<GoalsList />} />
              <Route path="/experiencias" element={<Experiences />} />
              <Route path="/patrimonio" element={<Patrimony />} />
              <Route path="/wealthness" element={<Wealthness />} />
              <Route path="/analisis" element={<Analysis />} />
              <Route path="/perfil" element={<ProfileSettings />} />

              {/* Paths from before the Spanish rename */}
              <Route path="/statements" element={<Navigate to="/extractos" replace />} />
              <Route path="/statements/upload" element={<Navigate to="/extractos/subir" replace />} />
              <Route path="/debts" element={<Navigate to="/deudas" replace />} />
              <Route path="/goals" element={<Navigate to="/metas" replace />} />
              <Route path="/analysis" element={<Navigate to="/analisis" replace />} />
              <Route path="/profile" element={<Navigate to="/perfil" replace />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
