import { useState, useEffect } from 'react';
import { Plus, Check, X, Palette, Type, Image, Sparkles, Camera } from 'lucide-react';
import { brand as brandApi } from '@/api/client';
import type { BrandGuideline } from '@/types';
import { useAuthStore } from '@/stores/authStore';
import clsx from 'clsx';

const BRAND_COLORS = [
  { name: 'Primary Orange', hex: '#FF6600' },
  { name: 'Dark Background', hex: '#1A1A2E' },
  { name: 'Accent Gold', hex: '#FFD700' },
  { name: 'White', hex: '#FFFFFF' },
  { name: 'Surface Blue', hex: '#16213E' },
];

const tabs = [
  { id: 'color', label: 'Colors', icon: Palette },
  { id: 'typography', label: 'Typography', icon: Type },
  { id: 'logo', label: 'Logo', icon: Image },
  { id: 'graphics', label: 'Graphics', icon: Sparkles },
  { id: 'imagery', label: 'Imagery', icon: Camera },
];

export default function GuidelinesPanel() {
  const [activeTab, setActiveTab] = useState('color');
  const [guidelines, setGuidelines] = useState<BrandGuideline[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [newName, setNewName] = useState('');
  const [newRules, setNewRules] = useState('');
  const { user } = useAuthStore();
  const isAdmin = user && ['admin', 'super_admin'].includes(user.role);

  useEffect(() => {
    brandApi.listGuidelines().then(setGuidelines).catch(() => {});
  }, []);

  const filtered = guidelines.filter((g) => g.category === activeTab);

  const handleAdd = async () => {
    if (!newName.trim()) return;
    try {
      const created = await brandApi.createGuideline({
        name: newName,
        category: activeTab,
        scope: 'global',
        rules: { description: newRules },
        is_active: true,
      });
      setGuidelines((prev) => [...prev, created]);
      setNewName('');
      setNewRules('');
      setShowAdd(false);
    } catch { /* ignore */ }
  };

  return (
    <div>
      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-[#16213E] rounded-xl p-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all flex-1 justify-center',
              activeTab === tab.id ? 'bg-primary/20 text-primary' : 'text-gray-400 hover:text-white'
            )}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Colors tab - special display */}
      {activeTab === 'color' && (
        <div className="grid grid-cols-5 gap-4 mb-6">
          {BRAND_COLORS.map((color) => (
            <div key={color.hex} className="card p-4 text-center">
              <div className="w-16 h-16 rounded-xl mx-auto mb-3 border border-white/10" style={{ backgroundColor: color.hex }} />
              <p className="text-sm font-medium text-white">{color.name}</p>
              <p className="text-xs text-gray-500 font-mono">{color.hex}</p>
            </div>
          ))}
        </div>
      )}

      {/* Guidelines list */}
      <div className="space-y-3">
        {filtered.map((g) => (
          <div key={g.id} className="card p-4 flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <h4 className="text-sm font-medium text-white">{g.name}</h4>
                <span className={clsx('badge text-[10px]', g.scope === 'global' ? 'badge-primary' : 'badge-accent')}>
                  {g.scope}
                </span>
                {g.market_id && <span className="badge badge-accent text-[10px]">Market-specific</span>}
              </div>
              <p className="text-xs text-gray-400">{typeof g.rules === 'object' ? JSON.stringify(g.rules) : g.rules}</p>
            </div>
            <div className={clsx('w-2 h-2 rounded-full mt-1', g.is_active ? 'bg-green-500' : 'bg-gray-600')} />
          </div>
        ))}

        {filtered.length === 0 && !showAdd && (
          <div className="text-center py-8 text-gray-500 text-sm">No guidelines for this category yet.</div>
        )}
      </div>

      {/* Add new */}
      {isAdmin && (
        <>
          {showAdd ? (
            <div className="card p-4 mt-4">
              <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Guideline name" className="input-field w-full mb-3" />
              <textarea value={newRules} onChange={(e) => setNewRules(e.target.value)} placeholder="Rules description..." className="input-field w-full mb-3" rows={3} />
              <div className="flex gap-2 justify-end">
                <button onClick={() => setShowAdd(false)} className="btn-ghost text-sm"><X className="w-4 h-4" /></button>
                <button onClick={handleAdd} className="btn-primary text-sm flex items-center gap-1"><Check className="w-4 h-4" /> Save</button>
              </div>
            </div>
          ) : (
            <button onClick={() => setShowAdd(true)} className="btn-secondary w-full mt-4 flex items-center justify-center gap-2">
              <Plus className="w-4 h-4" /> Add Guideline
            </button>
          )}
        </>
      )}
    </div>
  );
}
