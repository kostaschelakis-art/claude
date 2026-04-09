import { useState } from 'react';
import { X, Download, Loader2 } from 'lucide-react';
import { images as imagesApi } from '@/api/client';
import { DIMENSION_PRESETS, groupPresetsByCategory } from '@/utils/dimensions';

interface ExportDialogProps {
  imageId: string;
  onClose: () => void;
}

export default function ExportDialog({ imageId, onClose }: ExportDialogProps) {
  const [format, setFormat] = useState<'png' | 'jpg' | 'webp' | 'pdf'>('png');
  const [usePreset, setUsePreset] = useState(true);
  const [presetName, setPresetName] = useState(DIMENSION_PRESETS[0].name);
  const [customWidth, setCustomWidth] = useState(1080);
  const [customHeight, setCustomHeight] = useState(1080);
  const [quality, setQuality] = useState(95);
  const [exporting, setExporting] = useState(false);
  const grouped = groupPresetsByCategory();

  const selectedPreset = DIMENSION_PRESETS.find((p) => p.name === presetName);
  const finalWidth = usePreset ? (selectedPreset?.width ?? 1080) : customWidth;
  const finalHeight = usePreset ? (selectedPreset?.height ?? 1080) : customHeight;

  const handleExport = async () => {
    setExporting(true);
    try {
      const blob = await imagesApi.exportImage(imageId, format, finalWidth, finalHeight, quality);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `brandforge-${imageId.slice(0, 8)}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      onClose();
    } catch {
      alert('Export failed. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div className="card p-6 w-[480px] max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-white">Export Image</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white"><X className="w-5 h-5" /></button>
        </div>

        {/* Format */}
        <div className="mb-4">
          <label className="text-sm text-gray-400 mb-2 block">Format</label>
          <div className="grid grid-cols-4 gap-2">
            {(['png', 'jpg', 'webp', 'pdf'] as const).map((f) => (
              <button key={f} onClick={() => setFormat(f)} className={`py-2 rounded-lg text-sm font-medium transition-all ${format === f ? 'bg-primary text-white' : 'bg-white/5 text-gray-400 hover:bg-white/10'}`}>
                {f.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {/* Dimensions */}
        <div className="mb-4">
          <div className="flex items-center gap-3 mb-2">
            <button onClick={() => setUsePreset(true)} className={`text-sm ${usePreset ? 'text-primary font-medium' : 'text-gray-400'}`}>Preset</button>
            <span className="text-gray-600">|</span>
            <button onClick={() => setUsePreset(false)} className={`text-sm ${!usePreset ? 'text-primary font-medium' : 'text-gray-400'}`}>Custom</button>
          </div>
          {usePreset ? (
            <select value={presetName} onChange={(e) => setPresetName(e.target.value)} className="select-field w-full">
              {Object.entries(grouped).map(([cat, presets]) => (
                <optgroup key={cat} label={cat}>
                  {presets.map((p) => <option key={p.name} value={p.name}>{p.name} ({p.width}x{p.height})</option>)}
                </optgroup>
              ))}
            </select>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-500">Width</label>
                <input type="number" value={customWidth} onChange={(e) => setCustomWidth(Number(e.target.value))} className="input-field w-full" />
              </div>
              <div>
                <label className="text-xs text-gray-500">Height</label>
                <input type="number" value={customHeight} onChange={(e) => setCustomHeight(Number(e.target.value))} className="input-field w-full" />
              </div>
            </div>
          )}
        </div>

        {/* Quality (for JPG/WebP) */}
        {(format === 'jpg' || format === 'webp') && (
          <div className="mb-4">
            <label className="text-sm text-gray-400 mb-2 block">Quality: {quality}%</label>
            <input type="range" min={10} max={100} value={quality} onChange={(e) => setQuality(Number(e.target.value))} className="w-full accent-primary" />
          </div>
        )}

        {/* Preview */}
        <div className="bg-[#0F0F23] rounded-lg p-3 mb-6">
          <p className="text-xs text-gray-500">Export preview</p>
          <p className="text-sm text-white">{finalWidth} x {finalHeight} px &middot; {format.toUpperCase()}{(format === 'jpg' || format === 'webp') ? ` &middot; ${quality}%` : ''}</p>
        </div>

        <button onClick={handleExport} disabled={exporting} className="btn-primary w-full flex items-center justify-center gap-2">
          {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
          {exporting ? 'Exporting...' : 'Export'}
        </button>
      </div>
    </div>
  );
}
