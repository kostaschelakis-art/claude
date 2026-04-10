import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import LoadingSpinner from '@/components/Common/LoadingSpinner';

export default function OAuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { loadUser } = useAuthStore();

  useEffect(() => {
    const token = searchParams.get('token');
    const error = searchParams.get('error');

    if (error) {
      navigate('/login?error=' + error);
      return;
    }

    if (token) {
      localStorage.setItem('brandforge_token', token);
      useAuthStore.setState({ token, isAuthenticated: true });
      loadUser().then(() => navigate('/'));
    } else {
      navigate('/login?error=no_token');
    }
  }, [searchParams, navigate, loadUser]);

  return (
    <div className="min-h-screen bg-[#0F0F23] flex items-center justify-center">
      <LoadingSpinner message="Signing you in..." />
    </div>
  );
}
