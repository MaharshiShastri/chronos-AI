import React from 'react';
import NeumorphicCard from './NeumorphicCard';
import { Send } from 'lucide-react';

const ChatPanel = ({
  messages,
  input,
  setInput,
  onSend,
  loading,
  scrollRef
}) => {
  return (
    <div className="flex-1 flex flex-col h-full space-y-6 p-6">
      
      {/* MESSAGE AREA */}
      <NeumorphicCard className="flex-1 flex flex-col overflow-hidden" inset>
        <div className="flex-1 overflow-y-auto pr-2 space-y-6">
          {messages.map((m, idx) => (
            <div key={idx} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`
                max-w-[70%] p-4 rounded-2xl
                ${m.role === 'user' 
                  ? 'bg-cyan-950 text-cyan-100 rounded-br-lg' 
                  : 'bg-slate-800 text-slate-100 rounded-bl-lg shadow-md'}
              `}>
                <span className="text-sm font-mono text-slate-400">{m.role === 'user' ? 'USER_LOG' : 'LOGIC_ENGINE'}</span>
                <p className="mt-1">{m.content}</p>
              </div>
            </div>
          ))}
          <div ref={scrollRef} /> {/* For auto-scroll */}
        </div>
      </NeumorphicCard>

      {/* INPUT BAR */}
      <NeumorphicCard>
        <div className="flex items-center gap-4 bg-slate-800 rounded-xl p-2 pr-4 shadow-inner">
          <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && onSend()}
            placeholder="SYSTEM INPUT or //mission request..."
            className="flex-1 bg-transparent p-2 outline-none text-white placeholder-slate-500"
            disabled={loading}
          />
          <button 
            onClick={onSend}
            disabled={loading}
            className={`p-2 rounded-lg text-cyan-200 ${loading ? 'opacity-50' : 'bg-cyan-950 hover:bg-cyan-900'}`}
          >
            <Send size={18} />
          </button>
        </div>
      </NeumorphicCard>
    </div>
  );
};

export default ChatPanel;