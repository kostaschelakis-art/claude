import { ThumbsUp, ThumbsDown, Star } from 'lucide-react';
import type { QAScore } from '@/types';
import clsx from 'clsx';
import { useState } from 'react';

interface QAScoreCardProps {
  qaScore: QAScore;
  onFeedback?: (rating: number, thumbsUp: boolean) => void;
}

function CircularScore({ score }: { score: number }) {
  const color = score >= 80 ? '#22c55e' : score >= 50 ? '#eab308' : '#ef4444';
  const circumference = 2 * Math.PI * 45;
  const dashOffset = circumference - (score / 100) * circumference;

  return (
    <div className="relative w-28 h-28">
      <svg className="transform -rotate-90 w-28 h-28">
        <circle cx="56" cy="56" r="45" stroke="#1A1A3E" strokeWidth="8" fill="none" />
        <circle cx="56" cy="56" r="45" stroke={color} strokeWidth="8" fill="none" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={dashOffset} className="transition-all duration-1000" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold" style={{ color }}>{Math.round(score)}</span>
        <span className="text-[10px] text-gray-500">/ 100</span>
      </div>
    </div>
  );
}

export default function QAScoreCard({ qaScore, onFeedback }: QAScoreCardProps) {
  const [userRating, setUserRating] = useState(0);
  const [thumbs, setThumbs] = useState<boolean | null>(null);

  const handleThumbsFeedback = (up: boolean) => {
    setThumbs(up);
    onFeedback?.(userRating || (up ? 5 : 1), up);
  };

  return (
    <div className="card p-5">
      <div className="flex items-start gap-5 mb-5">
        <CircularScore score={qaScore.overall_score} />
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-white mb-1">QA Score</h3>
          <p className="text-xs text-gray-400 leading-relaxed">{qaScore.explanation}</p>
        </div>
      </div>

      {/* Category Breakdown */}
      <div className="space-y-2 mb-5">
        {Object.entries(qaScore.category_scores).map(([category, data]) => (
          <div key={category}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-gray-400 capitalize">{category.replace('_', ' ')}</span>
              <span className="text-gray-300">{Math.round(data.score)}</span>
            </div>
            <div className="h-1.5 bg-[#0F0F23] rounded-full overflow-hidden">
              <div
                className={clsx('h-full rounded-full transition-all duration-700', data.score >= 80 ? 'bg-green-500' : data.score >= 50 ? 'bg-yellow-500' : 'bg-red-500')}
                style={{ width: `${data.score}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Violations */}
      {qaScore.violations.length > 0 && (
        <div className="mb-4">
          <h4 className="text-xs font-medium text-gray-400 mb-2">Violations</h4>
          <div className="space-y-1">
            {qaScore.violations.map((v, i) => (
              <div key={i} className={clsx('text-xs px-3 py-2 rounded-lg', v.severity === 'critical' ? 'bg-red-500/10 text-red-400' : v.severity === 'major' ? 'bg-orange-500/10 text-orange-400' : 'bg-yellow-500/10 text-yellow-400')}>
                <span className="font-medium capitalize">[{v.severity}]</span> {v.description}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Suggestions */}
      {qaScore.suggestions.length > 0 && (
        <div className="mb-4">
          <h4 className="text-xs font-medium text-gray-400 mb-2">Suggestions</h4>
          <ul className="space-y-1">
            {qaScore.suggestions.map((s, i) => (
              <li key={i} className="text-xs text-gray-300 flex gap-2"><span className="text-primary">-</span>{s}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Feedback */}
      <div className="border-t border-white/5 pt-4 flex items-center justify-between">
        <div className="flex gap-2">
          <button onClick={() => handleThumbsFeedback(true)} className={clsx('p-2 rounded-lg transition-colors', thumbs === true ? 'bg-green-500/20 text-green-400' : 'text-gray-500 hover:text-green-400 hover:bg-green-500/10')}>
            <ThumbsUp className="w-4 h-4" />
          </button>
          <button onClick={() => handleThumbsFeedback(false)} className={clsx('p-2 rounded-lg transition-colors', thumbs === false ? 'bg-red-500/20 text-red-400' : 'text-gray-500 hover:text-red-400 hover:bg-red-500/10')}>
            <ThumbsDown className="w-4 h-4" />
          </button>
        </div>
        <div className="flex gap-0.5">
          {[1, 2, 3, 4, 5].map((star) => (
            <button key={star} onClick={() => { setUserRating(star); onFeedback?.(star, thumbs ?? star >= 3); }}
              className={clsx('p-0.5 transition-colors', star <= userRating ? 'text-accent' : 'text-gray-600 hover:text-accent/50')}>
              <Star className="w-4 h-4" fill={star <= userRating ? 'currentColor' : 'none'} />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
