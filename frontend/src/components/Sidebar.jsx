import React from 'react';
import NeumorphicCard from './NeumorphicCard';
import { LogOut, Zap, Edit2, Trash2, Plus, Layout, Clock, X } from 'lucide-react';

const Sidebar = ({
  conversations,
  tasks,
  activeId,
  onSelectConv,
  onDeleteConv,
  onDeleteTask,
  onStartRename,
  onLogout
}) => {
  return (
    <nav className="w-80 h-full p-6 flex flex-col space-y-8 bg-slate-950 border-r border-slate-800">
      
      {/* 1. ARCHIVES Section */}
      <NeumorphicCard className="flex-1 flex flex-col space-y-4 overflow-hidden" inset>
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-400">ARCHIVES</h2>
          <button className="text-cyan-500"><Plus size={18} /></button>
        </div>
        
        <div className="flex-1 space-y-3 overflow-y-auto pr-2">
          {conversations.map(c => (
            <div 
              key={c.id} 
              onClick={() => onSelectConv(c.id)}
              className={`group flex items-center justify-between p-3 rounded-lg cursor-pointer transition ${c.id === parseInt(activeId) ? 'bg-cyan-950/40 text-cyan-200' : 'hover:bg-slate-800/50'}`}
            >
              <div className="flex items-center gap-3">
                <Layout size={16} />
                <span className="text-sm truncate w-40">{c.title || `Session_${c.id}`}</span>
              </div>
              <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition">
                <button onClick={(e) => onStartRename(c.id, c.title, e)}><Edit2 size={14} /></button>
                <button onClick={(e) => onDeleteConv(c.id, e)}><Trash2 size={14} className="text-red-400" /></button>
              </div>
            </div>
          ))}
        </div>
      </NeumorphicCard>

      {/* 2. OBJECTIVES (MISSION LOG) Section */}
      <NeumorphicCard className="h-64 flex flex-col space-y-4 overflow-hidden" inset>
        <h2 className="text-sm font-semibold text-slate-400">OBJECTIVES LOG</h2>
        <div className="flex-1 space-y-3 overflow-y-auto pr-2">
          {tasks.map(t => (
            <div key={t.id} className="group flex items-center justify-between p-3 rounded-lg bg-slate-800/30">
              <div className="flex items-center gap-3">
                <Clock size={16} className={t.status === 'completed' ? 'text-green-400' : 'text-yellow-400'} />
                <span className="text-sm truncate w-40">{t.title}</span>
              </div>
              <button 
                onClick={(e) => onDeleteTask(t.id, e)}
                className="opacity-0 group-hover:opacity-100 transition text-red-400"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      </NeumorphicCard>

      {/* 3. LOGOUT Button */}
      <NeumorphicCard>
        <button 
          onClick={onLogout}
          className="w-full flex items-center justify-center gap-3 p-3 bg-red-950 rounded-xl text-red-100 hover:bg-red-900 transition"
        >
          <LogOut size={18} />
          <span>TERMINATE_SESSION</span>
        </button>
      </NeumorphicCard>
    </nav>
  );
};

export default Sidebar;