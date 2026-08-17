/**
 * Router guards (used in App.tsx).
 *
 * - ProtectedRoute: gates every dashboard route; unauthenticated users are
 *   redirected to /login while the session is still loading.
 * - PublicOnlyRoute: prevents signed-in users from visiting /login or
 *   /register, sending them straight to the dashboard instead.
 */
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from './AuthContext';

export function ProtectedRoute() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

export function PublicOnlyRoute() {
  const { user } = useAuth();

  if (user) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}