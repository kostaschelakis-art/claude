import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { Zap, Loader2 } from 'lucide-react';

export default function Login() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const { login, isLoading } = useAuthStore();
  const navigate = useNavigate();

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

  const handleSSOLogin = () => {
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
          {/* SSO Login */}
          <button onClick={handleSSOLogin} className="btn-primary w-full mb-6 py-3 text-base">
            Login with Kaizen SSO
          </button>

          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-white/10" /></div>
            <div className="relative flex justify-center"><span className="px-3 bg-[#1A1A3E] text-xs text-gray-500">or dev login</span></div>
          </div>

          {/* Dev Login */}
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
              Dev Login
            </button>
          </form>
        </div>

        <p className="text-center text-gray-600 text-xs mt-6">Betano Brand Asset Generation Platform v1.0</p>
      </div>
    </div>
  );
}
