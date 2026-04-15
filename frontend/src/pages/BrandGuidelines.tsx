import GuidelinesPanel from '@/components/Brand/GuidelinesPanel';
import { Upload, Loader2 } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { brand as brandApi } from '@/api/client';

interface BrandAsset {
  id: string;
  name: string;
  asset_type: string;
  file_url: string;
}

export default function BrandGuidelines() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [assets, setAssets] = useState<BrandAsset[]>([]);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<{ kind: 'success' | 'error'; text: string } | null>(null);

  const loadAssets = async () => {
    try {
      const list = (await brandApi.listAssets()) as BrandAsset[];
      setAssets(list || []);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    loadAssets();
  }, []);

  const handleUploadAsset = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ''; // allow re-selecting the same file
    if (!file) return;
    setUploading(true);
    setMessage(null);
    try {
      await brandApi.uploadAsset(file, 'logo');
      setMessage({ kind: 'success', text: `Uploaded "${file.name}".` });
      await loadAssets();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setMessage({
        kind: 'error',
        text: `Upload failed${detail ? `: ${detail}` : '. Check the backend logs.'}`,
      });
    } finally {
      setUploading(false);
      setTimeout(() => setMessage(null), 5000);
    }
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Brand Guidelines</h1>
          <p className="text-gray-400 text-sm mt-1">Manage brand rules that apply to all generated images.</p>
        </div>
        <div>
          <button
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="btn-secondary flex items-center gap-2 disabled:opacity-60"
          >
            {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            {uploading ? 'Uploading...' : 'Upload Brand Asset'}
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            onChange={handleUploadAsset}
            className="hidden"
          />
        </div>
      </div>

      {message && (
        <div
          className={
            message.kind === 'success'
              ? 'bg-green-500/10 border border-green-500/20 text-green-400 rounded-lg p-3 mb-4 text-sm'
              : 'bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg p-3 mb-4 text-sm'
          }
        >
          {message.text}
        </div>
      )}

      {assets.length > 0 && (
        <div className="mb-8">
          <h2 className="text-sm font-medium text-gray-300 mb-3">Uploaded Assets</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-4">
            {assets.map((asset) => (
              <div key={asset.id} className="card p-3">
                <div className="aspect-square bg-[#0F0F23] rounded-lg overflow-hidden flex items-center justify-center mb-2">
                  <img
                    src={asset.file_url}
                    alt={asset.name}
                    className="max-w-full max-h-full object-contain"
                  />
                </div>
                <p className="text-xs text-white truncate" title={asset.name}>{asset.name}</p>
                <p className="text-[10px] text-gray-500">{asset.asset_type}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <GuidelinesPanel />
    </div>
  );
}
