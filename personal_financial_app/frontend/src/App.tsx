/**
 * Application entry component: auth provider + client-side router.
 *
 * Public routes (login/register) are wrapped in PublicOnlyRoute, every
 * dashboard route sits behind ProtectedRoute inside the shared FullLayout.
 */
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { ProtectedRoute, PublicOnlyRoute } from './auth/ProtectedRoute';
import FullLayout from './layouts/FullLayout';
import Login from './pages/Login';
import Register from './pages/Register';
import AnalyticsDashboard from './components/analytics/AnalyticsDashboard';
import StatementList from './components/statements/StatementList';
import StatementUploader from './components/statements/StatementUploader';
import StatementReview from './components/statements/StatementReview';
import DebtRegistry from './components/debts/DebtRegistry';
import DebtDetail from './components/debts/DebtDetail';
import GoalsList from './components/goals/GoalsList';
import Analysis from './components/analysis/Analysis';
import ProfileSettings from './components/profile/ProfileSettings';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<PublicOnlyRoute />}>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
          </Route>

          <Route element={<ProtectedRoute />}>
            <Route element={<FullLayout />}>
              <Route path="/" element={<AnalyticsDashboard />} />
              <Route path="/statements" element={<StatementList />} />
              <Route path="/statements/upload" element={<StatementUploader />} />
              <Route path="/statements/:id/review" element={<StatementReview />} />
              <Route path="/debts" element={<DebtRegistry />} />
              <Route path="/debts/:id" element={<DebtDetail />} />
              <Route path="/goals" element={<GoalsList />} />
              <Route path="/analysis" element={<Analysis />} />
              <Route path="/profile" element={<ProfileSettings />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;