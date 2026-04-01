import React from 'react';
import NeumorphicCard from './NeumorphicCard';
import { ChevronLeft, Zap, Check, Edit2, Trash2 } from 'lucide-react';
import ExecutionView from './ExecutionView'; // Assuming this already works

const PlanPanel = ({
  activePlan,
  loading,
  timeBudget,
  setTimeBudget,
  planMode,
  setPlanMode,
  onBack,
  onRequestPlan
}) => {
  return (
    <div className="flex-1 flex flex-col h-full space-y-6 p-6">
      
      {/* 1. HEADER (Back Button & Summary) */}
      <NeumorphicCard className="flex items-center justify-between">
        <button onClick={onBack} className="flex items-center gap-2 text-slate-400 hover:text-cyan-200">
          <ChevronLeft size={18} />
          <span>BACK_TO_CHAT</span>
        </button>
        <h1 className="text-xl font-bold text-cyan-300">MISSION_CONTROL</h1>
      </NeumorphicCard>

      {/* 2. MAIN CONTENT (Config or Step View) */}
      {(!activePlan && !loading) ? (
        // PLAN CONFIGURATION SCREEN
        <NeumorphicCard className="flex-1 flex flex-col justify-center items-center space-y-8" inset>
          <Zap size={64} className="text-yellow-400 animate-pulse" />
          <h2 className="text-2xl font-bold">CONFIGURE SYSTEM OBJECTIVE</h2>
          
          <div className="w-1/2 space-y-6">
            <div>
              <label className="block text-sm text-slate-400 mb-2">Time Budget (Seconds)</label>
              <input type="range" min="300" max="1800" step="300" value={timeBudget} onChange={(e) => setTimeBudget(e.target.value)} className="w-full h-2 rounded-lg cursor-pointer bg-cyan-950 accent-cyan-400" />
              <p className="text-center font-mono mt-1 text-cyan-300">{timeBudget}s ({(timeBudget / 60).toFixed(0)} min)</p>
            </div>
            
            <div className="flex gap-4">
              <button onClick={() => setPlanMode('fast')} className={`w-1/2 p-3 rounded-lg border ${planMode === 'fast' ? 'bg-cyan-950 text-cyan-200 border-cyan-400' : 'bg-slate-800 border-slate-700'}`}>FAST_EXECUTION</button>
              <button onClick={() => setPlanMode('deep')} className={`w-1/2 p-3 rounded-lg border ${planMode === 'deep' ? 'bg-cyan-950 text-cyan-200 border-cyan-400' : 'bg-slate-800 border-slate-700'}`}>DEEP_ANALYSIS</button>
            </div>

            <button onClick={onRequestPlan} className="w-full flex items-center justify-center gap-3 p-4 bg-cyan-950 rounded-xl text-cyan-100 hover:bg-cyan-900 transition">
              <Zap size={18} />
              <span>INITIALIZE_PLANNING_STREAM</span>
            </button>
          </div>
        </NeumorphicCard>
      ) : loading ? (
        // LOADING SPINNER
        <NeumorphicCard className="flex-1 flex justify-center items-center" inset>
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400"></div>
        </NeumorphicCard>
      ) : activePlan && (
        // ACTIVE PLAN / EXECUTION VIEW
        <NeumorphicCard className="flex-1 overflow-y-auto" inset>
          {/* We assume ExecutionView already handles its own display within this card */}
          <ExecutionView mission_id={activePlan.mission_id} steps={activePlan.steps} />
        </NeumorphicCard>
      )}
    </div>
  );
};

export default PlanPanel;