import { Eye, EyeOff, Lock, Unlock, Trash2, ChevronUp, ChevronDown } from 'lucide-react';
import type { ImageLayer } from '@/types';
import clsx from 'clsx';

interface LayerPanelProps {
  layers: ImageLayer[];
  selectedLayerId: string | null;
  onSelectLayer: (id: string) => void;
  onToggleVisibility: (id: string) => void;
  onToggleLock: (id: string) => void;
  onDeleteLayer: (id: string) => void;
  onMoveLayer: (id: string, direction: 'up' | 'down') => void;
  onOpacityChange: (id: string, opacity: number) => void;
  visibilityState: Record<string, boolean>;
  lockState: Record<string, boolean>;
}

const layerTypeColors: Record<string, string> = {
  background: 'bg-blue-500/20 text-blue-400',
  subject: 'bg-green-500/20 text-green-400',
  text: 'bg-purple-500/20 text-purple-400',
  logo: 'bg-primary/20 text-primary',
  overlay: 'bg-accent/20 text-accent',
  effect: 'bg-pink-500/20 text-pink-400',
};

export default function LayerPanel(props: LayerPanelProps) {
  const { layers, selectedLayerId, onSelectLayer, onToggleVisibility, onToggleLock, onDeleteLayer, onMoveLayer, onOpacityChange, visibilityState, lockState } = props;

  return (
    <div className="w-72 bg-[#16213E] border-l border-white/5 flex flex-col h-full">
      <div className="p-3 border-b border-white/5">
        <h3 className="text-sm font-semibold text-white">Layers</h3>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {layers.sort((a, b) => b.layer_index - a.layer_index).map((layer) => {
          const isSelected = layer.id === selectedLayerId;
          const isVisible = visibilityState[layer.id] !== false;
          const isLocked = lockState[layer.id] === true;
          const typeColor = layerTypeColors[layer.layer_type] || 'bg-gray-500/20 text-gray-400';

          return (
            <div
              key={layer.id}
              onClick={() => onSelectLayer(layer.id)}
              className={clsx(
                'rounded-lg p-2 cursor-pointer transition-all border',
                isSelected ? 'bg-primary/10 border-primary/30' : 'border-transparent hover:bg-white/5'
              )}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className={clsx('badge text-[10px]', typeColor)}>{layer.layer_type}</span>
                <span className="text-xs text-gray-300 flex-1 truncate">Layer {layer.layer_index}</span>
                <button onClick={(e) => { e.stopPropagation(); onToggleVisibility(layer.id); }} className="p-0.5 hover:text-white text-gray-500">
                  {isVisible ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
                </button>
                <button onClick={(e) => { e.stopPropagation(); onToggleLock(layer.id); }} className="p-0.5 hover:text-white text-gray-500">
                  {isLocked ? <Lock className="w-3.5 h-3.5" /> : <Unlock className="w-3.5 h-3.5" />}
                </button>
              </div>
              {isSelected && (
                <div className="flex items-center gap-1 mt-2">
                  <input
                    type="range" min="0" max="100" defaultValue={100}
                    onChange={(e) => onOpacityChange(layer.id, Number(e.target.value) / 100)}
                    className="flex-1 h-1 accent-primary"
                    onClick={(e) => e.stopPropagation()}
                  />
                  <button onClick={(e) => { e.stopPropagation(); onMoveLayer(layer.id, 'up'); }} className="p-0.5 text-gray-500 hover:text-white"><ChevronUp className="w-3.5 h-3.5" /></button>
                  <button onClick={(e) => { e.stopPropagation(); onMoveLayer(layer.id, 'down'); }} className="p-0.5 text-gray-500 hover:text-white"><ChevronDown className="w-3.5 h-3.5" /></button>
                  <button onClick={(e) => { e.stopPropagation(); onDeleteLayer(layer.id); }} className="p-0.5 text-gray-500 hover:text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
