import { Loader2 } from 'lucide-react';
import clsx from 'clsx';

export default function LoadingSpinner({ message, className }: { message?: string; className?: string }) {
  return (
    <div className={clsx('flex flex-col items-center justify-center gap-3', className)}>
      <Loader2 className="w-8 h-8 text-primary animate-spin" />
      {message && <p className="text-gray-400 text-sm">{message}</p>}
    </div>
  );
}
