import GuidelinesPanel from '@/components/Brand/GuidelinesPanel';
import { Upload } from 'lucide-react';
import { useRef } from 'react';
import { brand as brandApi } from '@/api/client';

export default function BrandGuidelines() {
  const fileRef = useRef<HTMLInputElement>(null);

  const handleUploadAsset = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await brandApi.uploadAsset(file);
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Brand Guidelines</h1>
          <p className="text-gray-400 text-sm mt-1">Manage brand rules that apply to all generated images.</p>
        </div>
        <div>
          <button onClick={() => fileRef.current?.click()} className="btn-secondary flex items-center gap-2">
            <Upload className="w-4 h-4" /> Upload Brand Asset
          </button>
          <input ref={fileRef} type="file" onChange={handleUploadAsset} className="hidden" />
        </div>
      </div>
      <GuidelinesPanel />
    </div>
  );
}
