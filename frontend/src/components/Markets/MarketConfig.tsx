import { useState, useEffect } from 'react';
import { Plus, Save, Trash2, Globe, Shield } from 'lucide-react';
import { markets as marketsApi } from '@/api/client';
import type { Market, LegalDisclaimer } from '@/types';
import { useAuthStore } from '@/stores/authStore';
import clsx from 'clsx';

export default function MarketConfig() {
  const [marketList, setMarketList] = useState<Market[]>([]);
  const [selectedMarket, setSelectedMarket] = useState<Market | null>(null);
  const [disclaimerText, setDisclaimerText] = useState('');
  const [saving, setSaving] = useState(false);
  const { user } = useAuthStore();
  const isSuperAdmin = user?.role === 'super_admin';

  useEffect(() => {
    marketsApi.list().then(setMarketList).catch(() => {});
  }, []);

  const handleSaveLegal = async () => {
    if (!selectedMarket) return;
    setSaving(true);
    try {
      const newDisclaimer: LegalDisclaimer = { text: disclaimerText, position: 'bottom', font_size: 12, required: true };
      const updated = await marketsApi.updateLegal(selectedMarket.id, [...(selectedMarket.legal_disclaimers || []), newDisclaimer]);
      setSelectedMarket(updated);
      setMarketList((prev) => prev.map((m) => (m.id === updated.id ? updated : m)));
      setDisclaimerText('');
    } catch { /* ignore */ }
    setSaving(false);
  };

  const handleRemoveDisclaimer = async (index: number) => {
    if (!selectedMarket) return;
    const updated = await marketsApi.updateLegal(
      selectedMarket.id,
      selectedMarket.legal_disclaimers.filter((_, i) => i !== index)
    );
    setSelectedMarket(updated);
    setMarketList((prev) => prev.map((m) => (m.id === updated.id ? updated : m)));
  };

  return (
    <div className="grid grid-cols-12 gap-6">
      {/* Market list */}
      <div className="col-span-4">
        <div className="card">
          <div className="p-4 border-b border-white/5 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Markets</h3>
            {isSuperAdmin && (
              <button className="btn-ghost text-xs flex items-center gap-1"><Plus className="w-3.5 h-3.5" /> Add</button>
            )}
          </div>
          <div className="p-2">
            {marketList.map((market) => (
              <button
                key={market.id}
                onClick={() => setSelectedMarket(market)}
                className={clsx(
                  'w-full flex items-center gap-3 p-3 rounded-lg text-left transition-all',
                  selectedMarket?.id === market.id ? 'bg-primary/10 border border-primary/20' : 'hover:bg-white/5 border border-transparent'
                )}
              >
                <Globe className="w-4 h-4 text-gray-400" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-white">{market.display_name}</p>
                  <p className="text-xs text-gray-500">{market.code}</p>
                </div>
                <div className={clsx('w-2 h-2 rounded-full', market.is_active ? 'bg-green-500' : 'bg-gray-600')} />
              </button>
            ))}
            {marketList.length === 0 && (
              <p className="text-center text-gray-500 text-sm py-6">No markets configured</p>
            )}
          </div>
        </div>
      </div>

      {/* Market details */}
      <div className="col-span-8">
        {selectedMarket ? (
          <div className="space-y-4">
            <div className="card p-5">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Globe className="w-5 h-5 text-primary" />
                {selectedMarket.display_name} ({selectedMarket.code})
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-gray-400">Status</label>
                  <p className={clsx('text-sm font-medium', selectedMarket.is_active ? 'text-green-400' : 'text-gray-500')}>
                    {selectedMarket.is_active ? 'Active' : 'Inactive'}
                  </p>
                </div>
              </div>
            </div>

            {/* Legal Disclaimers */}
            <div className="card p-5">
              <h4 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <Shield className="w-4 h-4 text-accent" />
                Legal Disclaimers
              </h4>
              <div className="space-y-2 mb-4">
                {(selectedMarket.legal_disclaimers || []).map((d, i) => (
                  <div key={i} className="flex items-center gap-3 bg-[#0F0F23] rounded-lg p-3">
                    <p className="text-sm text-gray-300 flex-1">{d.text}</p>
                    <span className="badge badge-accent text-[10px]">{d.position}</span>
                    <button onClick={() => handleRemoveDisclaimer(i)} className="text-gray-500 hover:text-red-400">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  value={disclaimerText}
                  onChange={(e) => setDisclaimerText(e.target.value)}
                  placeholder="Add legal disclaimer text..."
                  className="input-field flex-1"
                />
                <button onClick={handleSaveLegal} disabled={!disclaimerText.trim() || saving} className="btn-primary flex items-center gap-1">
                  <Save className="w-4 h-4" /> Save
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="card p-12 text-center">
            <Globe className="w-10 h-10 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400">Select a market to configure</p>
          </div>
        )}
      </div>
    </div>
  );
}
