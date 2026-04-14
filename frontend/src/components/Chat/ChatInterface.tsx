import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Settings2 } from 'lucide-react';
import { useImageStore } from '@/stores/imageStore';
import { useAuthStore } from '@/stores/authStore';
import { DIMENSION_PRESETS, groupPresetsByCategory } from '@/utils/dimensions';
import MessageBubble from './MessageBubble';
import type { ChatMessage } from '@/types';

export default function ChatInterface() {
  const [prompt, setPrompt] = useState('');
  const [showOptions, setShowOptions] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState(DIMENSION_PRESETS[0]);
  const [provider, setProvider] = useState('google');
  const { chatMessages, addChatMessage, isGenerating, generate } = useImageStore();
  const { user } = useAuthStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const grouped = groupPresetsByCategory();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const handleSend = async () => {
    if (!prompt.trim() || isGenerating) return;
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: prompt,
      timestamp: new Date().toISOString(),
    };
    addChatMessage(userMsg);
    setPrompt('');

    try {
      const image = await generate({
        prompt: userMsg.content,
        width: selectedPreset.width,
        height: selectedPreset.height,
        ai_provider: provider,
        market_id: user?.market_id,
      });

      const aiMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `Here's your generated image (${selectedPreset.name} - ${selectedPreset.width}x${selectedPreset.height}). QA Score: ${image.qa_score?.overall_score ?? 'pending'}/100\n\nWould you like to adjust anything? You can ask me to change colors, composition, or style.`,
        image_url: image.composite_url,
        image_id: image.id,
        timestamp: new Date().toISOString(),
      };
      addChatMessage(aiMsg);
    } catch {
      addChatMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: 'Sorry, there was an error generating the image. Please try again.',
        timestamp: new Date().toISOString(),
      });
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-2">
        {chatMessages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center mb-6">
              <Send className="w-8 h-8 text-primary" />
            </div>
            <h2 className="text-xl font-semibold text-white mb-2">Start Creating</h2>
            <p className="text-gray-400 max-w-md">Describe the image you want to generate. I'll apply brand guidelines automatically and provide a QA score.</p>
            <div className="flex gap-2 mt-6 flex-wrap justify-center">
              {['Sports promo banner with football theme', 'Casino welcome offer with neon style', 'Mission challenge card with dynamic composition'].map((s) => (
                <button key={s} onClick={() => setPrompt(s)} className="btn-ghost text-xs border border-white/10 rounded-full px-3 py-1.5">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {chatMessages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} qaScore={msg.image_url ? 85 : undefined} />
        ))}
        {isGenerating && (
          <div className="flex gap-3 mb-4">
            <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center text-accent text-xs font-bold flex-shrink-0">AI</div>
            <div className="bg-[#1A1A3E] border border-white/5 rounded-2xl px-4 py-3">
              <div className="flex items-center gap-2 text-gray-400 text-sm">
                <Loader2 className="w-4 h-4 animate-spin" />
                Generating your image...
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Options Panel */}
      {showOptions && (
        <div className="border-t border-white/5 bg-[#16213E] p-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Dimension Preset</label>
              <select value={selectedPreset.name} onChange={(e) => {
                const p = DIMENSION_PRESETS.find((p) => p.name === e.target.value);
                if (p) setSelectedPreset(p);
              }} className="select-field w-full text-sm">
                {Object.entries(grouped).map(([cat, presets]) => (
                  <optgroup key={cat} label={cat}>
                    {presets.map((p) => (
                      <option key={p.name} value={p.name}>{p.name} ({p.width}x{p.height})</option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">AI Provider</label>
              <select value={provider} onChange={(e) => setProvider(e.target.value)} className="select-field w-full text-sm">
                <option value="google">Google Imagen</option>
                <option value="openai">OpenAI DALL-E 3</option>
                <option value="stability">Stability AI</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Dimensions</label>
              <p className="text-white text-sm mt-1">{selectedPreset.width} x {selectedPreset.height} px</p>
            </div>
          </div>
        </div>
      )}

      {/* Input */}
      <div className="border-t border-white/5 bg-[#16213E] p-4">
        <div className="flex gap-3 items-end">
          <button onClick={() => setShowOptions(!showOptions)} className={`btn-ghost p-2.5 rounded-lg ${showOptions ? 'text-primary' : ''}`}>
            <Settings2 className="w-5 h-5" />
          </button>
          <div className="flex-1 relative">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              placeholder="Describe the image you want to generate..."
              rows={1}
              className="input-field w-full resize-none pr-12"
            />
          </div>
          <button onClick={handleSend} disabled={!prompt.trim() || isGenerating} className="btn-primary p-2.5 rounded-lg">
            {isGenerating ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
          </button>
        </div>
      </div>
    </div>
  );
}
