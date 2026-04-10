import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { Zap, Loader2 } from 'lucide-react';

export default function Login() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const { login, isLoading } = useAuthStore();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const urlError = searchParams.get('error');

  const handleDevLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await login(email);
      navigate('/');
    } catch {
      setError('Login failed. Please try again.');
    }
  };

  const handleGoogleLogin = () => {
    window.location.href = '/api/v1/auth/oauth/login';
  };

  return (
    <div className="min-h-screen bg-[#0F0F23] flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-accent flex items-center justify-center mx-auto mb-4">
            <Zap className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gradient">BrandForge</h1>
          <p className="text-gray-400 mt-2">AI-Powered Image Generation Platform</p>
        </div>

        <div className="card p-8">
          {urlError && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 mb-6">
              <p className="text-red-400 text-sm">
                {urlError === 'inactive' ? 'Your account has been deactivated. Contact an administrator.' : 'Sign in failed. Please try again.'}
              </p>
            </div>
          )}

          {/* Google Sign-In */}
          <button
            onClick={handleGoogleLogin}
            className="w-full flex items-center justify-center gap-3 bg-white hover:bg-gray-100 text-gray-800 font-medium py-3 px-6 rounded-lg transition-all duration-200 active:scale-95 mb-6"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Sign in with Google
          </button>

          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-white/10" /></div>
            <div className="relative flex justify-center"><span className="px-3 bg-[#1A1A3E] text-xs text-gray-500">or use email</span></div>
          </div>

          {/* Email Login */}
          <form onSubmit={handleDevLogin}>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
              className="input-field w-full mb-4"
              required
            />
            {error && <p className="text-red-400 text-sm mb-3">{error}</p>}
            <button type="submit" disabled={isLoading || !email} className="btn-secondary w-full flex items-center justify-center gap-2">
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              Sign in with Email
            </button>
          </form>
        </div>

        <p className="text-center text-gray-600 text-xs mt-6">Betano Brand Asset Generation Platform v1.0</p>
      </div>
    </div>
  );
}
