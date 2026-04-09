import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, Plus, LayoutTemplate, Filter } from 'lucide-react';
import { templates as templatesApi } from '@/api/client';
import { useAuthStore } from '@/stores/authStore';
import type { Template } from '@/types';
import clsx from 'clsx';
import LoadingSpinner from '../Common/LoadingSpinner';

const categories = ['All', 'email', 'story', 'push', 'slider', 'promo_banner', 'in_app', 'newsletter', 'casino', 'sports', 'custom'];

export default function TemplateGallery() {
  const [templateList, setTemplateList] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState('All');
  const [analyzing, setAnalyzing] = useState(false);
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { user } = useAuthStore();
  const isAdmin = user && ['admin', 'super_admin'].includes(user.role);

  useEffect(() => {
    const params = activeCategory === 'All' ? {} : { category: activeCategory };
    templatesApi.list(params).then(setTemplateList).catch(() => {}).finally(() => setLoading(false));
  }, [activeCategory]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAnalyzing(true);
    try {
      const template = await templatesApi.analyze(file);
      setTemplateList((prev) => [template, ...prev]);
    } catch { /* ignore */ }
    setAnalyzing(false);
  };

  return (
    <div>
      {/* Filters */}
      <div className="flex items-center gap-3 mb-6 flex-wrap">
        <Filter className="w-4 h-4 text-gray-500" />
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={clsx(
              'px-3 py-1.5 rounded-full text-xs font-medium transition-all',
              activeCategory === cat ? 'bg-primary text-white' : 'bg-white/5 text-gray-400 hover:bg-white/10'
            )}
          >
            {cat === 'All' ? 'All' : cat.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Actions */}
      <div className="flex gap-3 mb-6">
        <button onClick={() => fileInputRef.current?.click()} className="btn-secondary flex items-center gap-2" disabled={analyzing}>
          <Upload className="w-4 h-4" /> {analyzing ? 'Analyzing...' : 'Upload & Analyze'}
        </button>
        <input ref={fileInputRef} type="file" accept="image/*" onChange={handleUpload} className="hidden" />
        {isAdmin && (
          <button className="btn-primary flex items-center gap-2"><Plus className="w-4 h-4" /> Create New</button>
        )}
      </div>

      {loading ? (
        <LoadingSpinner message="Loading templates..." className="py-20" />
      ) : templateList.length === 0 ? (
        <div className="text-center py-20">
          <LayoutTemplate className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-400 mb-2">No templates yet</h3>
          <p className="text-sm text-gray-500">Upload an image to analyze it as a template, or create one manually.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {templateList.map((template) => (
            <div key={template.id} className="card overflow-hidden group hover:border-primary/30 transition-all">
              <div className="aspect-[4/3] bg-[#0F0F23] flex items-center justify-center relative">
                <LayoutTemplate className="w-10 h-10 text-gray-700" />
                <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <button onClick={() => navigate(`/generate?template=${template.id}`)} className="btn-primary text-xs">
                    Use Template
                  </button>
                </div>
                <span className="absolute top-2 right-2 badge badge-primary text-[10px]">{template.category}</span>
              </div>
              <div className="p-3">
                <h4 className="text-sm font-medium text-white truncate">{template.name}</h4>
                <p className="text-xs text-gray-500">{template.dimensions_width} x {template.dimensions_height}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
