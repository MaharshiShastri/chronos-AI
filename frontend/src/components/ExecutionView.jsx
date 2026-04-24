import React, { useState, useMemo, useEffect } from 'react';
import NeumorphicCard from './NeumorphicCard';
import { CheckCircle2, Circle} from 'lucide-react';
import { aiService } from '../services/api';

const ExecutionView = ({ plan, onComplete }) => {
  // --- STATE ---
  const [currentStep, setCurrentStep] = useState(0);
  const [timeLeft, setTimeLeft] = useState(0);
  const [totalStepTime, setTotalStepTime] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [isFinished, setIsFinished] = useState(false); 
  const [approvalData, setApprovalData] = useState(null);
  const [activeMissionId, setActiveMissionId] = useState(null);
  const [editableArtifact, setEditableArtifact] = useState("");
  const [localSteps, setLocalSteps] = useState([]);

  // Sync initial plan steps
  useEffect(() => { 
    const initialSteps = plan?.enriched_steps || plan?.steps || [];
    if(Array.isArray(initialSteps) && initialSteps.length > 0) {
      setLocalSteps(initialSteps);
    }
  }, [plan]);

  const allSteps = useMemo(() => localSteps, [localSteps]);
  const totalStepCount = allSteps.length || 1;

  useEffect(() => {
    if (plan?.mission_id || plan?.id) {
      setActiveMissionId(plan.mission_id || plan.id);
    }
  }, [plan]);

  // --- TIMER LOGIC ---
  useEffect(() => {
    let timer;
    if (isExecuting && !isPaused && timeLeft > 0) {
      timer = setInterval(() => {
        setTimeLeft(prev => Math.max(0, prev - 1));
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [isExecuting, isPaused, timeLeft]);

  // --- MISSION CONTROL ---
  const startMission = () => {
  if (!activeMissionId) return;
  setIsExecuting(true);
  setIsFinished(false);

  aiService.executeMission(activeMissionId, (payload) => {
  console.log("Received Event:", payload.event, payload); // Add this debug log
  
  switch (payload.event) {
    case "MANIFEST":
      if(payload.steps) setLocalSteps(payload.steps);
      break;

    case "STEP_STARTED":
      const idx = payload.index ?? 0;
      setCurrentStep(idx);
      const stepTime = payload.steps?.[idx]?.time_allocated || localSteps[idx]?.time_allocated || 60;
      setTimeLeft(stepTime);
      setTotalStepTime(stepTime);
      setIsPaused(false);
      break;
    case "REQUIRE_APPROVAL":
      setIsPaused(true);
      setApprovalData({
        step_id: payload.step_id || payload.backend_step_id,
        index: payload.index,
        artifact: payload.content?.artifact,
        estimated: localSteps[payload.index]?.time_allocated || 0,
        actual: payload.content?.time_needed || 0,
        drift: payload.content?.drift || 0
      });
      setEditableArtifact(payload.content?.artifact || "");
      break;
      
    case "MISSION_COMPLETED":
      setIsExecuting(false);
      setIsFinished(true);
      break;

    case "ERROR":
      console.error("Execution Error:", payload.detail);
      setIsExecuting(false);
      break;
  }
});
  }
  const handleApproval = async (decision) => {
    if (!activeMissionId || !approvalData?.step_id) return;

    try {
      let finalStatus;
      if (approvalData.type === "CLARIFICATION") {
        finalStatus = "started"; // This breaks the 'awaiting_clarification' loop
      } else {
        finalStatus = decision === 'approve' ? 'completed' : 'refined';
      }
      await aiService.approveStep(activeMissionId, status, approvalData.step_id, editableArtifact);
      setApprovalData(null);
      setIsPaused(false);
    } catch (err) {
      console.error("API_APPROVAL_FAILED:", err);
    }
  };

  const stepProgress = totalStepTime > 0 ? (timeLeft / totalStepTime) * 100 : 0;

  return (
    <div className="flex-1 flex flex-col p-6 overflow-hidden">
      <NeumorphicCard className="flex-1 flex flex-col overflow-hidden bg-[#0f172a]/50 border-slate-800">
        
        {/* HEADER */}
        <div className="p-6 border-b border-slate-800/60">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-4">
               <div className="relative flex items-center justify-center">
                  <svg className="w-16 h-16 transform -rotate-90">
                    <circle cx="32" cy="32" r="28" stroke="currentColor" strokeWidth="3" fill="transparent" className="text-slate-800" />
                    <circle cx="32" cy="32" r="28" stroke="currentColor" strokeWidth="3" fill="transparent" 
                      strokeDasharray={175.9} 
                      strokeDashoffset={175.9 - (175.9 * stepProgress) / 100} 
                      className="text-cyan-500 transition-all duration-1000 ease-linear" />
                  </svg>
                  <span className="absolute text-[10px] font-black font-mono text-white">{Math.round(timeLeft)}S</span>
               </div>
               <div>
                  <h2 className="text-[10px] font-black text-cyan-500 tracking-widest uppercase">
                    {isFinished ? "COMPLETED" : isPaused ? "PAUSED" : "ACTIVE"}
                  </h2>
                  <p className="text-xl font-black uppercase italic">
                    Step {currentStep + 1} <span className="text-slate-600">/ {totalStepCount}</span>
                  </p>
               </div>
            </div>
            {!isExecuting && !isFinished && (
              <button onClick={startMission} className="px-6 py-3 bg-cyan-500 rounded-full text-black font-black uppercase text-[10px] hover:bg-cyan-400 transition-colors">
                Initiate_Protocol
              </button>
            )}
          </div>
        </div>

        {/* SCROLLABLE BODY */}
        <div className="flex-1 min-h-0 overflow-y-auto p-6 space-y-6 custom-scrollbar">
          {allSteps.map((s, idx) => {
            const isCompleted = idx < currentStep || isFinished;
            const isActive = idx === currentStep && !isFinished;
            return (
              <div key={idx} className={`p-5 rounded-2xl border transition-all duration-500 ${isActive ? 'bg-slate-800/60 border-cyan-500/50 scale-[1.02]' : 'border-transparent opacity-40'}`}>
                <div className="flex items-start gap-4">
                  <div className="mt-1">
                    {isCompleted ? <CheckCircle2 size={20} className="text-emerald-500" /> : <Circle size={20} className={isActive ? "text-cyan-500 animate-pulse" : "text-slate-700"} />}
                  </div>
                  <div className="flex-1">
                    <p className={`text-sm font-black uppercase tracking-tight ${isActive ? 'text-white' : 'text-slate-400'}`}>
                      {s.description || s.step || "Initializing..."}
                    </p>

                    {isActive && approvalData && (
                      <div className="mt-6 space-y-4 animate-in">
                        <div className="grid grid-cols-3 gap-3">
                           <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-700">
                             <span className="text-[8px] text-slate-500 uppercase block font-black">Estimated</span>
                             <span className="text-xs font-mono text-slate-300">{approvalData.estimated}s</span>
                           </div>
                           <div className="bg-cyan-500/10 p-3 rounded-xl border border-cyan-500/30">
                             <span className="text-[8px] text-cyan-500 uppercase block font-black">Used</span>
                             <span className="text-xs font-mono text-cyan-400">{approvalData.actual}s</span>
                           </div>
                           <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-700">
                             <span className="text-[8px] text-amber-500 uppercase block font-black">Drift</span>
                             <span className="text-xs font-mono text-amber-500">+{approvalData.drift}s</span>
                           </div>
                        </div>
                        <div className="space-y-2">
                          <label className="text-[9px] text-slate-400 uppercase font-black tracking-widest">Edit Artifact Result:</label>
                          <textarea 
                            value={editableArtifact}
                            onChange={(e) => setEditableArtifact(e.target.value)}
                            className="w-full bg-black/60 border border-slate-700 rounded-xl p-4 text-xs text-slate-300 font-mono focus:border-cyan-500 outline-none min-h-[120px] resize-none transition-colors"
                          />
                        </div>

                        <div className="flex gap-3 pt-2">
                          <button onClick={() => handleApproval('refine')} className="flex-1 py-4 bg-slate-800 hover:bg-slate-700 text-white text-[10px] font-black rounded-xl uppercase tracking-widest transition-all">Refine</button>
                          <button onClick={() => handleApproval('approve')} className="flex-1 py-4 bg-emerald-500 hover:bg-emerald-400 text-black text-[10px] font-black rounded-xl uppercase tracking-widest transition-all">Approve</button>
                        </div> 
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
          <div className="h-4" />
        </div>
      </NeumorphicCard>
    </div>
    );
  };

export default ExecutionView;
