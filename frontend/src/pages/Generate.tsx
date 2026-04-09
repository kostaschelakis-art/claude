import ChatInterface from '@/components/Chat/ChatInterface';

export default function Generate() {
  return (
    <div className="h-screen flex flex-col">
      <div className="p-6 pb-0 border-b border-white/5">
        <h1 className="text-lg font-semibold text-white mb-4">Generate Image</h1>
      </div>
      <div className="flex-1 overflow-hidden">
        <ChatInterface />
      </div>
    </div>
  );
}
