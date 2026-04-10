import React, { useState, useEffect, useMemo } from 'react';
import NeumorphicCard from './NeumorphicCard';
import { ChevronLeft, Zap, Target, CheckCircle2, Circle} from 'lucide-react';
import { aiService } from '../services/api';

const PlanPanel = ({ onBack, input, setInput }) => {
  // --- UI & CONFIG STATE ---
  const [status, setStatus] = useState('idle'); // 'idle' | 'planning' | 'executing'
  const [timeBudget, setTimeBudget] = useState(600);
  const [planMode, setPlanMode] = useState('fast');

  // --- EXECUTION DATA STATE ---
  const [activeMissionId, setActiveMissionId] = useState(null);
  const [steps, setSteps] = useState([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [timeLeft, setTimeLeft] = useState(0);
  const [totalStepTime, setTotalStepTime] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [approvalData, setApprovalData] = useState(null);
  const [editableArtifact, setEditableArtifact] = useState("");

  // --- 1. THE PLANNING STREAM ---
  const startPlanning = async () => {
    if (!input.trim()) return;
    
    setStatus('planning');
    setSteps(Array(6).fill({ description: "ANALYZING_PHASE...", status: 'ghost' }));

    try {
      await aiService.streamPlan(input, timeBudget, null, planMode, (data) => {
        // Handle incremental steps appearing
        if (data.single_step) {
          setSteps(prev => {
          const newSteps = [...prev];
          const desc = data.single_step.step || data.single_step.description;
          // Replace the first 'ghost' found with real data
          const ghostIdx = newSteps.findIndex(s => s.status === 'ghost');
          if (ghostIdx !== -1) {
            newSteps[ghostIdx] = { ...data.single_step, description: desc, status: 'pending' };
          } else {
            newSteps.push({ ...data.single_step, description: desc, status: 'pending' });
          }
          return newSteps;
        });
        }

        // Handle final DB sync
        if (data.status === 'complete') {
          setActiveMissionId(data.mission_id);
          // Sync final enriched steps from DB
          const finalized = data.enriched_steps.map(s => ({
            id: s.backend_step_id,
            description: s.description,
            time_allocated: s.time_allocated,
            status: 'pending'
        }));

        setSteps(finalized); 
        setStatus('executing')
        }
      });
    } catch (err) {
      console.error("Planning Failed:", err);
      setSteps([]);
      setStatus('idle');
      alert("Mission Planning Failed: The AI remains silent.");
    }
  };

  // --- 2. THE EXECUTION ENGINE ---
  const initiateProtocol = () => {
    if (!activeMissionId) return;
    setIsPaused(false);

    aiService.executeMission(activeMissionId, (payload) => {
      switch (payload.event) {
        case "MANIFEST":
          if (payload.steps && payload.steps.length > 0) {
            // This is the "Truth" from the DB. 
            // It will have all 6 steps, fixing the 1/1 issue instantly.
            setSteps(payload.steps.map(s => ({
              id: s.backend_step_id || s.id,
              description: s.description,
              time_allocated: s.time_allocated,
              status: s.status
            })));
          }
          break;
        case "STEP_STARTED":
          const idx = payload.index ?? 0;
          console.log("MOVING_TO_STEP:", payload.index);
          setCurrentStep(idx);
          const duration = payload.steps?.[idx]?.time_allocated || steps[idx]?.time_allocated || 60;
          setTimeLeft(duration);
          setTotalStepTime(duration);
          setIsPaused(false);
          setApprovalData(null);
          break;

        case "REQUIRE_APPROVAL":
          setIsPaused(true);
          setApprovalData({
            step_id: payload.step_id,
            index: payload.index,
            artifact: payload.content?.artifact,
            estimated: steps[payload.index]?.time_allocated || 0,
            actual: payload.content?.time_needed || 0,
            drift: payload.content?.drift || 0
          });
          setEditableArtifact(payload.content?.artifact || "");
          break;
        case "STEP_COMPLETED":
          console.log(`Step ${payload.index} verified.`);
          setSteps(prev => prev.map((s, i) => i === payload.index ? { ...s, status: 'completed' } : s));
          setApprovalData(null);
          break;
        case "MISSION_COMPLETED":
          setStatus('idle');
          setActiveMissionId(null);
          setSteps([]);
          break;
      }
    });
  };

  // Timer Effect
  useEffect(() => {
    let timer;
    if (status === 'executing' && !isPaused && timeLeft > 0) {
      timer = setInterval(() => setTimeLeft(p => Math.max(0, p - 1)), 1000);
    }
    return () => clearInterval(timer);
  }, [status, isPaused, timeLeft]);

  const handleApproval = async (decision) => {
    const finalStatus = decision === 'approve' ? 'completed' : 'refined';
    await aiService.approveStep(activeMissionId, finalStatus, approvalData.step_id, editableArtifact);
    setApprovalData(null);
    setIsPaused(false);
  };
  const displayTotal = steps.length > 0 ? steps.length : 6;
  const progress = totalStepTime > 0 ? (timeLeft / totalStepTime) * 100 : 0;

  // --- RENDER LOGIC ---
  return (
    <div className="flex-1 flex flex-col p-6 h-full overflow-hidden min-h-0">
      {/* SHARED HEADER */}
      <div className="flex items-center justify-between mb-6 px-2">
        <button onClick={onBack} className="flex items-center gap-2 text-slate-500 hover:text-white transition group">
          <ChevronLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
          <span className="text-[10px] font-black uppercase tracking-widest">Abort_Mission</span>
        </button>
      </div>

      <NeumorphicCard className="flex-1 flex flex-col overflow-hidden min-h-0" inset>
        
        {/* STATE 1: IDLE (Mission Config) */}
        {status === 'idle' && (
          <div className="p-12 max-w-2xl mx-auto space-y-10 overflow-y-auto custom-scrollbar">
            <div className="space-y-2">
              <div className="flex items-center gap-3 text-orange-400">
                <Target size={24} />
                <h1 className="text-3xl font-black tracking-tighter uppercase">Mission_Control</h1>
              </div>
            </div>
            <div className="space-y-8 bg-slate-900/40 p-8 rounded-3xl border border-slate-800/50">
              <textarea 
                value={input} onChange={(e) => setInput(e.target.value)}
                placeholder="Enter mission parameters..."
                className="w-full bg-slate-950 border border-slate-800 rounded-2xl p-4 text-sm text-slate-200 outline-none min-h-[120px] resize-none"
              />
              <div className="grid grid-cols-2 gap-8">
                <div className="space-y-4">
                  <label className="text-[10px] font-bold text-slate-500 uppercase">Budget: {timeBudget}s</label>
                  <input type="range" min="60" max="3600" step="60" value={timeBudget} onChange={(e) => setTimeBudget(e.target.value)} className="w-full accent-cyan-500" />
                </div>
                <div className="space-y-4">
                  <label className="text-[10px] font-bold text-slate-500 uppercase">Mode</label>
                  <div className="flex gap-2">
                    {['fast', 'deep'].map(m => (
                      <button key={m} onClick={() => setPlanMode(m)} className={`flex-1 py-2 rounded-lg text-[9px] font-black uppercase border ${planMode === m ? 'bg-cyan-900/40 text-cyan-400 border-cyan-500/30' : 'bg-slate-900 text-slate-600 border-slate-800'}`}>{m}</button>
                    ))}
                  </div>
                </div>
              </div>
              <button onClick={startPlanning} className="w-full py-4 bg-cyan-600 hover:bg-cyan-500 text-white rounded-2xl font-black text-xs uppercase tracking-widest transition-all">Initialize_Planning_Stream</button>
            </div>
          </div>
        )}

        {/* STATE 2: PLANNING (Loading with Preview) */}
        {status === 'planning' && (
          <div className="flex-1 flex flex-col items-center justify-center p-12 min-h-0">
            <Zap size={48} className="text-yellow-500 animate-pulse mb-4" />
            <p className="text-[10px] font-mono text-slate-500 tracking-[0.3em] mb-8">BUILDING_STRATEGY...</p>
            <div className="w-full max-w-md space-y-3">
              {steps.map((s, i) => (
                <div key={i} className="w-full max-w-md space-y-3 overflow-y-auto max-h-[300px] custom-scrollbar pr-2">
                  {`> STEP_${i+1}: ${s.description}`}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* STATE 3: EXECUTING */}
        {status === 'executing' && (
          <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
            <div className="p-6 border-b border-slate-800/60 flex justify-between items-center bg-slate-900/20">
               <div className="flex items-center gap-4">
                  <div className="relative w-12 h-12">
                    <svg className="w-full h-full -rotate-90">
                      <circle cx="24" cy="24" r="20" stroke="currentColor" strokeWidth="2" fill="transparent" className="text-slate-800" />
                      <circle cx="24" cy="24" r="20" stroke="currentColor" strokeWidth="2" fill="transparent" strokeDasharray="125.6" strokeDashoffset={125.6 - (125.6 * progress) / 100} className="text-cyan-500 transition-all duration-1000" />
                    </svg>
                    <span className="absolute inset-0 flex items-center justify-center text-[8px] font-mono">{timeLeft}S</span>
                  </div>
                  <div>
                    <h2 className="text-[9px] font-black text-cyan-500 uppercase tracking-widest">{isPaused ? 'PAUSED' : 'ACTIVE'}</h2>
                    <p className="text-lg font-black uppercase italic">Step {currentStep + 1} <span className="text-slate-600">/ {displayTotal}</span></p>
                  </div>
               </div>
               {timeLeft === 0 && !isPaused && (
                 <button onClick={initiateProtocol} className="px-6 py-2 bg-cyan-500 text-black text-[10px] font-black uppercase rounded-full hover:bg-cyan-400">Initiate_Protocol</button>
               )}
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar min-h-0">
              {steps.map((s, idx) => {
                const isComp = idx < currentStep;
                const isAct = idx === currentStep;
                return (
                  <div key={idx} className={`p-4 rounded-xl border transition-all duration-500 ${isAct ? 'bg-slate-800/40 border-cyan-500/40 scale-[1.01] shadow-[0_0_20px_rgba(56,189,248,0.05)]' : 'border-slate-800/50 opacity-40'}`}>
                    <div className="flex gap-3">
                      {isComp ? <CheckCircle2 size={18} className="text-emerald-500" /> : <Circle size={18} className={isAct ? "text-cyan-500 animate-pulse" : "text-slate-700"} />}
                      <div className="flex-1">
                        <p className="text-xs font-black uppercase tracking-tight text-slate-200">{s.description}</p>
                        {isAct && approvalData && (
                          <div className="mt-4 space-y-4 animate-in">
                            <textarea 
                              value={editableArtifact} 
                              onChange={(e) => setEditableArtifact(e.target.value)} 
                              className="w-full bg-black/40 border border-slate-700 rounded-lg p-3 text-[11px] font-mono min-h-[100px] text-cyan-50/90 outline-none focus:border-cyan-500/50 transition-colors custom-scrollbar" 
                            />
                            <div className="flex gap-2">
                              <button onClick={() => handleApproval('refine')} className="flex-1 py-2 bg-slate-800 hover:bg-slate-700 text-[9px] font-black uppercase rounded-lg transition-colors">Refine</button>
                              <button onClick={() => handleApproval('approve')} className="flex-1 py-2 bg-emerald-500 hover:bg-emerald-400 text-black text-[9px] font-black uppercase rounded-lg transition-colors">Approve</button>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
              <div className="h-4 w-full" />
            </div>
          </div>
        )}
      </NeumorphicCard>
    </div>
  );
};

export default PlanPanel;