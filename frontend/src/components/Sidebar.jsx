import React from 'react';
import { 
  Plus,
  Layout, 
  Trash2, 
  Edit2, 
  Terminal 
} from 'lucide-react';

const Sidebar = ({ conversations, activeId, onSelectConv, onLogout, onRename, onDelete, onNewChat }) => {
  return (
    <nav className="w-72 h-full p-6 flex flex-col bg-[#0a0f1a] animate-in slide-in-from-left duration-500">
      
      {/* HEADER & NEW SESSION */}
      <div className="flex flex-col gap-6 mb-8 px-2">
        <div className="flex items-center gap-2">
          <Terminal size={14} className="text-cyan-500" />
          <h2 className="text-[10px] font-black text-slate-500 tracking-[0.2em] uppercase">Archive_Index</h2>
        </div>
        
        <button 
          onClick={onNewChat}
          className="w-full py-3 px-4 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 flex items-center justify-center gap-2 hover:bg-cyan-500 hover:text-black transition-all duration-300 group"
        >
          <Plus size={16} className="group-hover:rotate-90 transition-transform" />
          <span className="text-[10px] font-black uppercase tracking-widest">New_Session</span>
        </button>
      </div>
      
      {/* CONVERSATION LIST */}
      <div className="flex-1 space-y-2 overflow-y-auto pr-2 custom-scrollbar">
        {conversations.map((c) => (
          <div 
            key={c.id}
            onClick={() => onSelectConv(c.id)}
            className={`group flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all border ${
              parseInt(activeId) === c.id 
                ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-200' 
                : 'hover:bg-slate-900/40 border-transparent text-slate-500 hover:text-slate-300'
            }`}
          >
            <div className="flex items-center gap-3 overflow-hidden flex-1">
              <Layout size={14} className={parseInt(activeId) === c.id ? 'text-cyan-400' : 'text-slate-700'} />
              <span className="text-[11px] font-bold uppercase tracking-tight truncate">
                {c.title || `Session_${c.id}`}
              </span>
            </div>

            {/* ACTION BUTTONS */}
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button 
                onClick={(e) => onRename(c.id, c.title, e)}
                className="p-1.5 hover:bg-white/10 rounded-md hover:text-cyan-400 text-slate-600 transition-colors"
              >
                <Edit2 size={12} />
              </button>
              <button 
                onClick={(e) => onDelete(c.id, e)}
                className="p-1.5 hover:bg-red-500/10 rounded-md hover:text-red-500 text-slate-600 transition-colors"
              >
                <Trash2 size={12} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* FOOTER */}
      <button 
        onClick={onLogout}
        className="mt-8 py-3 w-full bg-slate-900/30 border border-slate-800/50 rounded-xl text-slate-600 hover:text-red-400 transition-all font-black text-[9px] tracking-[0.2em] uppercase flex items-center justify-center gap-2"
      >
        Terminal_Exit
      </button>
    </nav>
  );
};

export default Sidebar;