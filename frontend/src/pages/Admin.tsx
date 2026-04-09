import { useState, useEffect } from 'react';
import { Users, BarChart3, FileText, Shield } from 'lucide-react';
import { admin as adminApi } from '@/api/client';
import type { User, AuditLog } from '@/types';
import clsx from 'clsx';

const tabs = [
  { id: 'users', label: 'Users', icon: Users },
  { id: 'usage', label: 'Usage Metrics', icon: BarChart3 },
  { id: 'audit', label: 'Audit Logs', icon: FileText },
];

export default function Admin() {
  const [activeTab, setActiveTab] = useState('users');
  const [users, setUsers] = useState<User[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);

  useEffect(() => {
    if (activeTab === 'users') adminApi.listUsers().then(setUsers).catch(() => {});
    if (activeTab === 'audit') adminApi.getAuditLogs({ limit: 50 }).then(setAuditLogs).catch(() => {});
  }, [activeTab]);

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      const updated = await adminApi.updateUserRole(userId, newRole);
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
    } catch { /* ignore */ }
  };

  return (
    <div className="p-8">
      <div className="flex items-center gap-3 mb-6">
        <Shield className="w-6 h-6 text-primary" />
        <h1 className="text-2xl font-bold text-white">Administration</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-[#16213E] rounded-xl p-1 w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              'flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all',
              activeTab === tab.id ? 'bg-primary/20 text-primary' : 'text-gray-400 hover:text-white'
            )}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Users Tab */}
      {activeTab === 'users' && (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/5">
                <th className="text-left text-xs text-gray-400 font-medium px-5 py-3">User</th>
                <th className="text-left text-xs text-gray-400 font-medium px-5 py-3">Email</th>
                <th className="text-left text-xs text-gray-400 font-medium px-5 py-3">Role</th>
                <th className="text-left text-xs text-gray-400 font-medium px-5 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-white/5 hover:bg-white/[0.02]">
                  <td className="px-5 py-3 text-sm text-white">{u.full_name || '-'}</td>
                  <td className="px-5 py-3 text-sm text-gray-400">{u.email}</td>
                  <td className="px-5 py-3">
                    <span className="badge badge-primary text-[10px] capitalize">{u.role.replace('_', ' ')}</span>
                  </td>
                  <td className="px-5 py-3">
                    <select
                      value={u.role}
                      onChange={(e) => handleRoleChange(u.id, e.target.value)}
                      className="select-field text-xs py-1 px-2"
                    >
                      <option value="viewer">Viewer</option>
                      <option value="creator">Creator</option>
                      <option value="admin">Admin</option>
                      <option value="super_admin">Super Admin</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {users.length === 0 && <p className="text-center text-gray-500 py-8">No users found</p>}
        </div>
      )}

      {/* Usage Tab */}
      {activeTab === 'usage' && (
        <div className="grid grid-cols-3 gap-4">
          <div className="card p-5">
            <p className="text-xs text-gray-400 mb-1">Generations This Month</p>
            <p className="text-3xl font-bold text-white">0</p>
          </div>
          <div className="card p-5">
            <p className="text-xs text-gray-400 mb-1">Estimated Cost</p>
            <p className="text-3xl font-bold text-white">$0.00</p>
          </div>
          <div className="card p-5">
            <p className="text-xs text-gray-400 mb-1">Active Users</p>
            <p className="text-3xl font-bold text-white">{users.length}</p>
          </div>
        </div>
      )}

      {/* Audit Logs Tab */}
      {activeTab === 'audit' && (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/5">
                <th className="text-left text-xs text-gray-400 font-medium px-5 py-3">Timestamp</th>
                <th className="text-left text-xs text-gray-400 font-medium px-5 py-3">User</th>
                <th className="text-left text-xs text-gray-400 font-medium px-5 py-3">Action</th>
                <th className="text-left text-xs text-gray-400 font-medium px-5 py-3">Resource</th>
                <th className="text-left text-xs text-gray-400 font-medium px-5 py-3">Details</th>
              </tr>
            </thead>
            <tbody>
              {auditLogs.map((log) => (
                <tr key={log.id} className="border-b border-white/5 hover:bg-white/[0.02]">
                  <td className="px-5 py-3 text-xs text-gray-500">{new Date(log.created_at).toLocaleString()}</td>
                  <td className="px-5 py-3 text-sm text-gray-300">{log.user_email}</td>
                  <td className="px-5 py-3"><span className="badge badge-primary text-[10px]">{log.action}</span></td>
                  <td className="px-5 py-3 text-sm text-gray-400">{log.resource_type}</td>
                  <td className="px-5 py-3 text-xs text-gray-500 max-w-xs truncate">{log.details}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {auditLogs.length === 0 && <p className="text-center text-gray-500 py-8">No audit logs yet</p>}
        </div>
      )}
    </div>
  );
}
