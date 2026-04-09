import type { ChatMessage } from '@/types';
import clsx from 'clsx';

function ScoreBadge({ score }: { score: number }) {
  const color = score >= 80 ? 'bg-green-500/20 text-green-400' : score >= 50 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-red-500/20 text-red-400';
  return <span className={clsx('badge', color)}>{score}/100</span>;
}

export default function MessageBubble({ message, qaScore }: { message: ChatMessage; qaScore?: number }) {
  const isUser = message.role === 'user';

  return (
    <div className={clsx('flex gap-3 mb-4', isUser ? 'flex-row-reverse' : 'flex-row')}>
      <div className={clsx('w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0', isUser ? 'bg-primary/20 text-primary' : 'bg-accent/20 text-accent')}>
        {isUser ? 'U' : 'AI'}
      </div>
      <div className={clsx('max-w-[70%] rounded-2xl px-4 py-3', isUser ? 'bg-primary/10 border border-primary/20' : 'bg-[#1A1A3E] border border-white/5')}>
        <p className="text-sm text-gray-200 whitespace-pre-wrap">{message.content}</p>
        {message.image_url && (
          <div className="mt-3 relative group">
            <img src={message.image_url} alt="Generated" className="rounded-lg max-h-64 object-cover w-full" />
            {qaScore !== undefined && (
              <div className="absolute top-2 right-2"><ScoreBadge score={qaScore} /></div>
            )}
            <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex items-center justify-center gap-2">
              <a href={`/editor/${message.image_id}`} className="btn-primary text-xs px-3 py-1.5">Edit</a>
              <button className="btn-secondary text-xs px-3 py-1.5">Export</button>
            </div>
          </div>
        )}
        <span className="text-[10px] text-gray-600 mt-1 block">{new Date(message.timestamp).toLocaleTimeString()}</span>
      </div>
    </div>
  );
}
