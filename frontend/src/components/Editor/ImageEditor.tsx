import { useState, useRef, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import ToolBar from './ToolBar';
import LayerPanel from './LayerPanel';
import ExportDialog from '../Export/ExportDialog';
import LoadingSpinner from '../Common/LoadingSpinner';
import { images as imagesApi } from '@/api/client';
import type { GeneratedImage, ImageLayer } from '@/types';

type Tool = 'select' | 'text' | 'logo' | 'shape' | 'effect' | 'safe_areas';

export default function ImageEditor() {
  const { id } = useParams<{ id: string }>();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [image, setImage] = useState<GeneratedImage | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTool, setActiveTool] = useState<Tool>('select');
  const [selectedLayerId, setSelectedLayerId] = useState<string | null>(null);
  const [showSafeAreas, setShowSafeAreas] = useState(false);
  const [showExport, setShowExport] = useState(false);
  const [visibilityState, setVisibilityState] = useState<Record<string, boolean>>({});
  const [lockState, setLockState] = useState<Record<string, boolean>>({});
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  useEffect(() => {
    if (!id) return;
    imagesApi.getImage(id).then((img) => {
      setImage(img);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!canvasRef.current || !image) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = image.width;
    canvas.height = image.height;

    // Draw background
    ctx.fillStyle = '#1A1A2E';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw composite image if available
    if (image.composite_url) {
      const img = new window.Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => {
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        if (showSafeAreas) drawSafeAreas(ctx, canvas.width, canvas.height);
      };
      img.src = image.composite_url;
    } else {
      // Draw placeholder
      ctx.fillStyle = '#2A2A4A';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#666';
      ctx.font = '24px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('Image Preview', canvas.width / 2, canvas.height / 2);
      if (showSafeAreas) drawSafeAreas(ctx, canvas.width, canvas.height);
    }
  }, [image, showSafeAreas, visibilityState]);

  const drawSafeAreas = (ctx: CanvasRenderingContext2D, w: number, h: number) => {
    // Title safe (80% center)
    ctx.strokeStyle = '#FFD700';
    ctx.lineWidth = 2;
    ctx.setLineDash([10, 5]);
    const titleMarginX = w * 0.1;
    const titleMarginY = h * 0.1;
    ctx.strokeRect(titleMarginX, titleMarginY, w - 2 * titleMarginX, h - 2 * titleMarginY);

    // Action safe (90% center)
    ctx.strokeStyle = '#FF6600';
    ctx.lineWidth = 1;
    const actionMarginX = w * 0.05;
    const actionMarginY = h * 0.05;
    ctx.strokeRect(actionMarginX, actionMarginY, w - 2 * actionMarginX, h - 2 * actionMarginY);
    ctx.setLineDash([]);

    // Labels
    ctx.font = '12px sans-serif';
    ctx.fillStyle = '#FFD700';
    ctx.fillText('Title Safe', titleMarginX + 5, titleMarginY + 15);
    ctx.fillStyle = '#FF6600';
    ctx.fillText('Action Safe', actionMarginX + 5, actionMarginY + 15);
  };

  const saveToHistory = useCallback(() => {
    if (!canvasRef.current) return;
    const dataUrl = canvasRef.current.toDataURL();
    setHistory((prev) => [...prev.slice(0, historyIndex + 1), dataUrl]);
    setHistoryIndex((prev) => prev + 1);
  }, [historyIndex]);

  const handleUndo = () => {
    if (historyIndex <= 0) return;
    setHistoryIndex((prev) => prev - 1);
  };

  const handleRedo = () => {
    if (historyIndex >= history.length - 1) return;
    setHistoryIndex((prev) => prev + 1);
  };

  if (loading) return <LoadingSpinner message="Loading editor..." className="h-full" />;
  if (!image) return <div className="flex items-center justify-center h-full text-gray-400">Image not found</div>;

  return (
    <div className="flex flex-col h-full">
      <ToolBar
        activeTool={activeTool}
        onToolChange={setActiveTool}
        onUndo={handleUndo}
        onRedo={handleRedo}
        onExport={() => setShowExport(true)}
        showSafeAreas={showSafeAreas}
        onToggleSafeAreas={() => setShowSafeAreas(!showSafeAreas)}
      />
      <div className="flex flex-1 overflow-hidden">
        {/* Canvas area */}
        <div className="flex-1 bg-[#0a0a1a] flex items-center justify-center p-8 overflow-auto">
          <div className="relative shadow-2xl">
            <canvas
              ref={canvasRef}
              className="max-w-full max-h-full"
              style={{ maxWidth: '100%', maxHeight: 'calc(100vh - 200px)' }}
              onClick={saveToHistory}
            />
          </div>
        </div>
        {/* Layer panel */}
        <LayerPanel
          layers={image.layers || []}
          selectedLayerId={selectedLayerId}
          onSelectLayer={setSelectedLayerId}
          onToggleVisibility={(id) => setVisibilityState((s) => ({ ...s, [id]: s[id] === false ? true : false }))}
          onToggleLock={(id) => setLockState((s) => ({ ...s, [id]: !s[id] }))}
          onDeleteLayer={() => {}}
          onMoveLayer={() => {}}
          onOpacityChange={() => {}}
          visibilityState={visibilityState}
          lockState={lockState}
        />
      </div>
      {showExport && <ExportDialog imageId={image.id} onClose={() => setShowExport(false)} />}
    </div>
  );
}
