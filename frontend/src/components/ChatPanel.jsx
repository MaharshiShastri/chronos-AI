import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { 
  Send, Zap, MessageSquare, X, 
  Loader2, CheckCircle, Plus, Layout 
} from 'lucide-react';
import { aiService } from '../services/api';

const ChatPanel = ({ 
  messages = [], 
  input, 
  setInput, 
  onSend, 
  loading, 
  scrollRef, 
  memories = [], 
  onMemoryChange // Using the name passed from ChatWindow.jsx
}) => {
  const [showUpload, setShowUpload] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('idle');

  // Logic to handle memory deletion directly from the overlay
  const handleDeleteMemory = async (id) => {
    try {
      await aiService.deleteMemory(id);
      if (onMemoryChange) onMemoryChange(); // Refresh state in ChatWindow
    } catch (err) {
      console.error("OVERLAY_DELETE_ERROR:", err);
    }
  };
  const safeMessages = Array.isArray(messages) ? messages : [];
  const safeMemories = Array.isArray(memories) ? memories : [];
  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploadStatus('uploading');
    try {
      await aiService.uploadDocument(file);
      setUploadStatus('success');
      setTimeout(() => {
        setUploadStatus('idle');
        setShowUpload(false);
      }, 2000);
    } catch (err) {
      console.error("Upload Failed", err);
      setUploadStatus('error');
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden relative">
      
      {/* 1. MESSAGE AREA */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
        {safeMessages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center opacity-20">
            <MessageSquare size={48} className="mb-4 text-slate-500" />
            <p className="text-[10px] font-black tracking-[0.4em] uppercase">System_Awaiting_Input</p>
          </div>
        )}
        
        {(messages || []).map((m, idx) => (
          <div key={idx} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] p-4 rounded-2xl shadow-lg border transition-all ${
              m.role === 'user' 
                ? 'bg-cyan-600/10 text-cyan-50 border-cyan-500/30 ml-12' 
                : 'bg-slate-800/50 text-slate-200 mr-12 border-slate-700/50 backdrop-blur-sm'
            }`}>
              <ReactMarkdown>{m.content || ""}</ReactMarkdown>
            </div>
          </div>
        ))}
        <div ref={scrollRef} /> 
      </div>

      {/* 2. KNOWLEDGE & MEMORY OVERLAY */}
      {showUpload && (
        <div className="absolute bottom-28 left-6 right-6 z-50 animate-in slide-in-from-bottom-4 duration-300">
          <div className="bg-[#0f172a] border border-indigo-500/40 rounded-[2rem] p-8 shadow-[0_20px_60px_rgba(0,0,0,0.7)] backdrop-blur-2xl">
            
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-indigo-600 rounded-lg">
                  <Zap size={16} className="text-white" />
                </div>
                <h2 className="text-[10px] font-black tracking-widest text-indigo-400 uppercase italic">Neural_System_Interface</h2>
              </div>
              <button onClick={() => setShowUpload(false)} className="text-slate-500 hover:text-white transition-colors">
                <X size={18} />
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Left Side: PDF Ingestion */}
              <div className="space-y-4">
                <h3 className="text-[9px] font-bold text-slate-500 uppercase tracking-[0.2em]">Vector_Ingestion</h3>
                <label className={`group relative border-2 border-dashed rounded-2xl p-8 transition-all flex flex-col items-center justify-center cursor-pointer min-h-[160px]
                    ${uploadStatus === 'uploading' ? 'border-indigo-500 bg-indigo-500/10' : 'border-slate-800 hover:border-indigo-500/50 bg-slate-950/20'}`}>
                  <input type="file" accept=".pdf" className="hidden" onChange={handleFileUpload} />
                  
                  {uploadStatus === 'idle' && (
                    <>
                      <Layout size={28} className="text-slate-700 mb-2 group-hover:text-indigo-400 transition-colors" />
                      <p className="text-[10px] text-slate-500 uppercase font-black tracking-tighter text-center">Inject PDF for<br/>Vector Grounding</p>
                    </>
                  )}

                  {uploadStatus === 'uploading' && (
                    <div className="flex flex-col items-center">
                      <Loader2 size={28} className="text-indigo-500 animate-spin mb-2" />
                      <p className="text-[10px] text-indigo-400 font-black animate-pulse uppercase">Embedding...</p>
                    </div>
                  )}

                  {uploadStatus === 'success' && (
                    <div className="flex flex-col items-center">
                      <CheckCircle size={28} className="text-emerald-500 mb-2" />
                      <p className="text-[10px] text-emerald-400 font-black uppercase">Sync_Complete</p>
                    </div>
                  )}
                </label>
              </div>

              {/* Right Side: Self-Evolution (Memories) */}
              <div className="space-y-4">
                <h3 className="text-[9px] font-bold text-cyan-500 uppercase tracking-[0.2em]">Self_Evolution_Records</h3>
                <div className="bg-slate-950/40 border border-slate-800/50 rounded-2xl p-4 h-[160px] overflow-y-auto custom-scrollbar">
                  {(!safeMemories || safeMemories.length === 0) ? (
                    <div className="h-full flex flex-col items-center justify-center opacity-30">
                      <p className="text-[9px] uppercase font-medium italic">No evolving facts detected...</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {(memories || []).map((mem) => (
                        <div key={mem.id} className="group flex items-start justify-between gap-3 bg-slate-900/30 p-2 rounded-lg border border-slate-800/50 hover:border-cyan-500/30 transition-all">
                          <p className="text-[11px] text-slate-300 leading-tight">
                            <span className="text-cyan-500 mr-2">●</span>
                            {/* Use fact_value to match VaultPanel and DB schema */}
                            {mem.fact_value}
                          </p>
                          <button 
                             onClick={() => handleDeleteMemory(mem.id)}
                             className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-red-400 transition-all"
                          >
                            <X size={12} />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 3. INPUT AREA */}
      <div className="p-6 bg-slate-950/50 border-t border-slate-800/60 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <button 
            onClick={() => setShowUpload(!showUpload)}
            className={`p-4 rounded-xl border transition-all duration-300 ${
              showUpload 
                ? 'bg-indigo-600 border-indigo-400 text-white rotate-45 shadow-[0_0_15px_rgba(79,70,229,0.4)]' 
                : 'bg-slate-900 border-slate-800 text-slate-500 hover:border-indigo-500/50'
            }`}
          >
            <Plus size={20} />
          </button>

          <div className="relative flex-1">
            <input 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && onSend()}
              placeholder={loading ? "SYSTEM_PROCESSING..." : "Input command or query knowledge..."}
              disabled={loading}
              className="w-full bg-slate-900/80 border border-slate-800 rounded-xl py-4 px-6 pr-16 outline-none focus:border-cyan-500/50 transition-all text-sm font-medium"
            />
            <button 
              onClick={onSend}
              disabled={loading || !input.trim()}
              className={`absolute right-3 top-1/2 -translate-y-1/2 p-2 transition-all ${
                loading || !input.trim() ? 'text-slate-700' : 'text-cyan-500 hover:text-cyan-300 active:scale-95'
              }`}
            >
              <Send size={20} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPanel;