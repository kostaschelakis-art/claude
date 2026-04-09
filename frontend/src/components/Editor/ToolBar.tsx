import { MousePointer2, Type, Image, Square, Sparkles, Grid3X3, Undo2, Redo2, Download } from 'lucide-react';
import clsx from 'clsx';

type Tool = 'select' | 'text' | 'logo' | 'shape' | 'effect' | 'safe_areas';

interface ToolBarProps {
  activeTool: Tool;
  onToolChange: (tool: Tool) => void;
  onUndo: () => void;
  onRedo: () => void;
  onExport: () => void;
  showSafeAreas: boolean;
  onToggleSafeAreas: () => void;
}

const tools: { id: Tool; icon: typeof MousePointer2; label: string }[] = [
  { id: 'select', icon: MousePointer2, label: 'Select' },
  { id: 'text', icon: Type, label: 'Text' },
  { id: 'logo', icon: Image, label: 'Logo' },
  { id: 'shape', icon: Square, label: 'Shape' },
  { id: 'effect', icon: Sparkles, label: 'Effects' },
];

export default function ToolBar(props: ToolBarProps) {
  const { activeTool, onToolChange, onUndo, onRedo, onExport, showSafeAreas, onToggleSafeAreas } = props;

  return (
    <div className="h-12 bg-[#16213E] border-b border-white/5 flex items-center px-4 gap-1">
      {tools.map((tool) => (
        <button
          key={tool.id}
          onClick={() => onToolChange(tool.id)}
          title={tool.label}
          className={clsx(
            'p-2 rounded-lg transition-colors',
            activeTool === tool.id ? 'bg-primary/20 text-primary' : 'text-gray-400 hover:text-white hover:bg-white/5'
          )}
        >
          <tool.icon className="w-4 h-4" />
        </button>
      ))}
      <div className="w-px h-6 bg-white/10 mx-2" />
      <button
        onClick={onToggleSafeAreas}
        title="Safe Areas"
        className={clsx('p-2 rounded-lg transition-colors', showSafeAreas ? 'bg-accent/20 text-accent' : 'text-gray-400 hover:text-white hover:bg-white/5')}
      >
        <Grid3X3 className="w-4 h-4" />
      </button>
      <div className="flex-1" />
      <button onClick={onUndo} className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-white/5" title="Undo"><Undo2 className="w-4 h-4" /></button>
      <button onClick={onRedo} className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-white/5" title="Redo"><Redo2 className="w-4 h-4" /></button>
      <div className="w-px h-6 bg-white/10 mx-2" />
      <button onClick={onExport} className="btn-primary text-xs px-3 py-1.5 flex items-center gap-1.5">
        <Download className="w-3.5 h-3.5" /> Export
      </button>
    </div>
  );
}
