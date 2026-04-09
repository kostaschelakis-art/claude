import { Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import {
  LayoutDashboard, Wand2, LayoutTemplate, Palette, Globe, Settings, LogOut, Zap,
} from 'lucide-react';
import clsx from 'clsx';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard, minRole: 'viewer' as const },
  { path: '/generate', label: 'Generate', icon: Wand2, minRole: 'creator' as const },
  { path: '/templates', label: 'Templates', icon: LayoutTemplate, minRole: 'viewer' as const },
  { path: '/brand', label: 'Brand Guidelines', icon: Palette, minRole: 'viewer' as const },
  { path: '/markets', label: 'Markets', icon: Globe, minRole: 'admin' as const },
  { path: '/admin', label: 'Admin', icon: Settings, minRole: 'super_admin' as const },
];

const roleOrder = ['viewer', 'creator', 'admin', 'super_admin'];

export default function Sidebar() {
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const userRoleIdx = user ? roleOrder.indexOf(user.role) : -1;

  return (
    <aside className="w-64 h-screen bg-[#16213E] border-r border-white/5 flex flex-col fixed left-0 top-0 z-40">
      {/* Logo */}
      <div className="p-6 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">BrandForge</h1>
            <p className="text-xs text-gray-400">AI Image Platform</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {navItems
          .filter((item) => userRoleIdx >= roleOrder.indexOf(item.minRole))
          .map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={clsx(
                  'flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 text-sm font-medium',
                  isActive
                    ? 'bg-primary/10 text-primary border border-primary/20'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                )}
              >
                <item.icon className="w-5 h-5" />
                {item.label}
              </Link>
            );
          })}
      </nav>

      {/* User info */}
      {user && (
        <div className="p-4 border-t border-white/5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-9 h-9 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold text-sm">
              {user.full_name?.charAt(0) || user.email.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{user.full_name || user.email}</p>
              <p className="text-xs text-gray-500 capitalize">{user.role.replace('_', ' ')}</p>
            </div>
          </div>
          <button onClick={logout} className="flex items-center gap-2 text-gray-400 hover:text-red-400 text-sm w-full px-2 py-1.5 rounded transition-colors">
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      )}
    </aside>
  );
}
