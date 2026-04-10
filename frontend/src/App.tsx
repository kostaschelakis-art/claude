import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { useEffect } from 'react';
import AppLayout from '@/components/Layout/AppLayout';
import Login from '@/pages/Login';
import Dashboard from '@/pages/Dashboard';
import Generate from '@/pages/Generate';
import EditorPage from '@/pages/Editor';
import Templates from '@/pages/Templates';
import BrandGuidelines from '@/pages/BrandGuidelines';
import Markets from '@/pages/Markets';
import Admin from '@/pages/Admin';
import OAuthCallback from '@/pages/OAuthCallback';

function ProtectedRoute({ children, minRole }: { children: React.ReactNode; minRole?: string }) {
  const { isAuthenticated, user } = useAuthStore();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  const roleOrder = ['viewer', 'creator', 'admin', 'super_admin'];
  if (minRole && user && roleOrder.indexOf(user.role) < roleOrder.indexOf(minRole)) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  const { loadUser, isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) loadUser();
  }, []);

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/oauth/callback" element={<OAuthCallback />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <AppLayout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/generate" element={<Generate />} />
                <Route path="/editor/:id" element={<EditorPage />} />
                <Route path="/templates" element={<Templates />} />
                <Route path="/brand" element={<BrandGuidelines />} />
                <Route path="/markets" element={<ProtectedRoute minRole="admin"><Markets /></ProtectedRoute>} />
                <Route path="/admin" element={<ProtectedRoute minRole="super_admin"><Admin /></ProtectedRoute>} />
              </Routes>
            </AppLayout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
