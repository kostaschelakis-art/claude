import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { useImageStore } from '@/stores/imageStore';
import { ImageIcon, Clock, BarChart3, LayoutTemplate, Wand2, Palette, ArrowRight } from 'lucide-react';
import type { GeneratedImage } from '@/types';

function StatCard({ icon: Icon, label, value, color }: { icon: typeof ImageIcon; label: string; value: string | number; color: string }) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-gray-400 mb-1">{label}</p>
          <p className="text-2xl font-bold text-white">{value}</p>
        </div>
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuthStore();
  const { images, loadImages } = useImageStore();
  const navigate = useNavigate();
  const [recentImages, setRecentImages] = useState<GeneratedImage[]>([]);

  useEffect(() => {
    loadImages({ limit: 8 });
  }, []);

  useEffect(() => {
    setRecentImages(images.slice(0, 8));
  }, [images]);

  const pendingReviews = images.filter((i) => i.status === 'review').length;
  const avgScore = images.length > 0
    ? Math.round(images.reduce((sum, i) => sum + (i.qa_score?.overall_score ?? 0), 0) / images.length)
    : 0;

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Welcome back, {user?.full_name || 'Creator'}</h1>
        <p className="text-gray-400 mt-1">Here's an overview of your creative workspace.</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard icon={ImageIcon} label="Total Images" value={images.length} color="bg-primary/20 text-primary" />
        <StatCard icon={Clock} label="Pending Reviews" value={pendingReviews} color="bg-yellow-500/20 text-yellow-400" />
        <StatCard icon={BarChart3} label="Avg QA Score" value={avgScore || '-'} color="bg-green-500/20 text-green-400" />
        <StatCard icon={LayoutTemplate} label="Templates" value={0} color="bg-accent/20 text-accent" />
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <button onClick={() => navigate('/generate')} className="card p-5 text-left hover:border-primary/30 transition-all group">
          <Wand2 className="w-6 h-6 text-primary mb-3" />
          <h3 className="font-medium text-white mb-1">Generate New Image</h3>
          <p className="text-xs text-gray-400">Create brand-compliant images with AI</p>
          <ArrowRight className="w-4 h-4 text-primary mt-3 opacity-0 group-hover:opacity-100 transition-opacity" />
        </button>
        <button onClick={() => navigate('/templates')} className="card p-5 text-left hover:border-accent/30 transition-all group">
          <LayoutTemplate className="w-6 h-6 text-accent mb-3" />
          <h3 className="font-medium text-white mb-1">Browse Templates</h3>
          <p className="text-xs text-gray-400">Start from existing layouts and designs</p>
          <ArrowRight className="w-4 h-4 text-accent mt-3 opacity-0 group-hover:opacity-100 transition-opacity" />
        </button>
        <button onClick={() => navigate('/brand')} className="card p-5 text-left hover:border-green-500/30 transition-all group">
          <Palette className="w-6 h-6 text-green-400 mb-3" />
          <h3 className="font-medium text-white mb-1">Brand Guidelines</h3>
          <p className="text-xs text-gray-400">Manage colors, typography, and rules</p>
          <ArrowRight className="w-4 h-4 text-green-400 mt-3 opacity-0 group-hover:opacity-100 transition-opacity" />
        </button>
      </div>

      {/* Recent Generations */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Recent Generations</h2>
          <button onClick={() => navigate('/generate')} className="btn-ghost text-xs">View All</button>
        </div>
        {recentImages.length > 0 ? (
          <div className="grid grid-cols-4 gap-4">
            {recentImages.map((img) => (
              <div key={img.id} className="card overflow-hidden cursor-pointer group" onClick={() => navigate(`/editor/${img.id}`)}>
                <div className="aspect-square bg-[#0F0F23] flex items-center justify-center relative">
                  {img.composite_url ? (
                    <img src={img.composite_url} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <ImageIcon className="w-8 h-8 text-gray-700" />
                  )}
                  {img.qa_score && (
                    <span className={`absolute top-2 right-2 badge ${img.qa_score.overall_score >= 80 ? 'badge-success' : img.qa_score.overall_score >= 50 ? 'badge-warning' : 'badge-error'}`}>
                      {Math.round(img.qa_score.overall_score)}
                    </span>
                  )}
                </div>
                <div className="p-3">
                  <p className="text-xs text-gray-300 truncate">{img.prompt}</p>
                  <p className="text-[10px] text-gray-600 mt-1">{img.width}x{img.height} &middot; {img.status}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="card p-12 text-center">
            <ImageIcon className="w-10 h-10 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400">No images generated yet. Start creating!</p>
          </div>
        )}
      </div>
    </div>
  );
}
