import React, { useState, useMemo, useEffect } from 'react';
import NeumorphicCard from './NeumorphicCard';
import { 
  CheckCircle2, 
  Circle, 
  Play, 
  ArrowRight, 
  ChevronLeft, 
  Timer, 
  AlertCircle, 
  Send, 
  Check 
} from 'lucide-react';
import { aiService } from '../services/api';

const ExecutionView = ({ plan, onComplete }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [timeLeft, setTimeLeft] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [localSteps, setLocalSteps] = useState([]);
  const [approvalData, setApprovalData] = useState(null);
  const [isExecuting, setIsExecuting] = useState(false);

  // 1. Data Normalization: Ensure we have a valid array of steps
  const steps = useMemo(() => {
    const rawSteps = plan?.enriched_steps || plan?.steps || [];
    return Array.isArray(rawSteps) ? rawSteps : [];
    // We stringify the steps so the memo only recalculates if the CONTENT changes
}, [JSON.stringify(plan?.steps), JSON.stringify(plan?.enriched_steps)]);

  // 2. Initialize local state when plan loads
  useEffect(() => {
    if (steps.length > 0 && localSteps.length === 0) {
      setLocalSteps(steps);
      setTimeLeft(steps[0].time_allocated || 60);
    }
  }, [steps]);

  // 3. Local Countdown Timer Logic
  useEffect(() => {
    if (timeLeft <= 0 || isPaused || !isExecuting) return;

    const timer = setInterval(() => {
      setTimeLeft(prev => (prev > 0 ? prev - 1 : 0));
    }, 1000);

    return () => clearInterval(timer);
  }, [timeLeft, isPaused, isExecuting]);

  // 4. Mission Execution Stream Handler
  const startMission = () => {
    setIsExecuting(true);
    const missionId = plan.mission_id || plan.id;

    aiService.executeMission(missionId,  (data) => {
      switch (data.event) {
        case "STEP_STARTED":
          setCurrentStep(data.index);
          // Sync with server's time remaining if provided, else use step allocation
          setTimeLeft(data.time_remaining || localSteps[data.index]?.time_allocated || 60);
          setIsPaused(false);
          break;

        case "REQUIRE_APPROVAL":
          setIsPaused(true);
          setApprovalData({
            index: data.index,
            content: data.content.artifact,
            drift: data.content.drift
          });
          break;

        case "STEP_COMPLETED":
          if (data.updated_steps) {
            setLocalSteps(data.updated_steps);
          }
          break;

        case "MISSION_COMPLETED":
          setIsExecuting(false);
          if (onComplete) onComplete();
          break;
          
        default:
          console.log("Unhandled SSE Event:", data.event);
      }
    });
  };

  const handleUserDecision = async (status) => {
    const missionId = plan.mission_id || plan.id;
    try {
      await aiService.approveStep(missionId, status, approvalData.content);
      setApprovalData(null);
      setIsPaused(false);
    } catch (err) {
      console.error("Failed to submit approval:", err);
    }
  };

  if (steps.length === 0) {
    return (
        <div className="flex-1 flex flex-col items-center justify-center p-20 space-y-4">
            <div className="w-10 h-10 border-2 border-sky-500/10 border-t-sky-500 rounded-full animate-spin"></div>
            <p className="text-sky-500 text-[10px] font-black animate-pulse uppercase tracking-widest">
                Awaiting_Sequence_Validation...
            </p>
        </div>
    );
}

  const progress = ((currentStep + (isExecuting ? 0.5 : 0)) / localSteps.length) * 100;

  return (
    <div className="w-full max-w-2xl mx-auto space-y-6 pb-10">
      
      {/* HEADER: GLOBAL MISSION STATUS */}
      <div className="flex justify-between items-end px-2">
        <div className="space-y-1">
          <span className="text-[10px] text-sky-500 font-black tracking-widest uppercase">Mission_Timeline</span>
          <div className="flex items-center gap-3">
             <Timer size={18} className={timeLeft < 10 && isExecuting ? "text-red-500 animate-pulse" : "text-sky-400"} />
             <span className={`text-2xl font-mono font-black ${timeLeft < 10 && isExecuting ? "text-red-500" : "text-white"}`}>
                {Math.floor(timeLeft / 60)}:{(timeLeft % 60).toString().padStart(2, '0')}
             </span>
          </div>
        </div>
        <div className="text-right">
          <span className="text-[10px] text-slate-500 font-black uppercase">Progress</span>
          <p className="text-xl font-mono text-sky-500">{Math.round(progress)}%</p>
        </div>
      </div>

      {/* PROGRESS BAR */}
      <div className="h-1.5 w-full bg-slate-900 rounded-full overflow-hidden border border-white/5 shadow-inner">
        <div 
          className="h-full bg-sky-500 transition-all duration-1000 shadow-[0_0_15px_#38bdf8]" 
          style={{ width: `${progress}%` }}
        />
      </div>

      <NeumorphicCard className="w-full">
        <div className="space-y-4">
          {/* INITIALIZE BUTTON */}
          {!isExecuting && currentStep === 0 && (
             <button 
                onClick={startMission}
                className="w-full py-4 bg-sky-500 text-slate-900 font-black rounded-xl shadow-lg shadow-sky-500/20 flex items-center justify-center gap-3 active:scale-[0.98] transition-transform"
             >
               <Play size={18} fill="currentColor"/> INITIATE_AGENT_SEQUENCER
             </button>
          )}

          {/* STEP LIST */}
          {localSteps.map((step, index) => {
            const isActive = index === currentStep;
            const isCompleted = index < currentStep;
            const isTimeout = isActive && timeLeft === 0 && isExecuting;
            
            return (
              <div 
                key={index} 
                className={`p-5 rounded-2xl border transition-all duration-500 ${
                  isActive 
                    ? 'bg-sky-500/5 border-sky-500/30 scale-[1.01] shadow-xl shadow-sky-900/10' 
                    : 'border-transparent opacity-40'
                }`}
              >
                <div className="flex gap-4">
                    <div className="mt-1">
                      {isCompleted ? (
                        <CheckCircle2 className="text-sky-500" size={20}/>
                      ) : isActive ? (
                        <div className={isTimeout ? "animate-pulse text-red-500" : "text-sky-400"}>
                          <Play size={20} fill="currentColor"/>
                        </div>
                      ) : (
                        <Circle className="text-slate-700" size={20}/>
                      )}
                    </div>

                    <div className="flex-1">
                        <div className="flex justify-between text-[9px] font-black font-mono mb-1">
                            <span className={isActive ? 'text-sky-400' : 'text-slate-500'}>
                              PHASE_{index+1} 
                              {isActive && <span className="ml-2 animate-pulse">● ACTIVE</span>}
                            </span>
                            <span className="text-slate-500">{step.time_allocated}S</span>
                        </div>
                        <p className={`text-sm ${isActive ? 'text-white' : 'text-slate-400'}`}>
                          {step.step || step.description}
                        </p>
                        
                        {/* INTERVENTION / APPROVAL UI */}
                        {isActive && approvalData && (
                          <div className="mt-4 p-4 bg-slate-900/80 border border-amber-500/30 rounded-xl space-y-3 animate-in fade-in slide-in-from-top-2">
                            <div className="flex justify-between items-center">
                                <span className="text-[10px] text-amber-500 font-black flex items-center gap-2">
                                  <AlertCircle size={12}/> ACTION_REQUIRED: VALIDATE_OUTPUT
                                </span>
                                {approvalData.drift > 0 && (
                                  <span className="text-[9px] text-red-400 font-mono">
                                    DRIFT: +{Math.round(approvalData.drift)}s
                                  </span>
                                )}
                            </div>
                            <textarea 
                                className="w-full bg-slate-800 p-3 rounded-lg text-xs text-slate-200 border border-white/5 focus:border-sky-500 outline-none transition-colors"
                                rows={4}
                                value={approvalData.content}
                                onChange={(e) => setApprovalData({...approvalData, content: e.target.value})}
                            />
                            <div className="flex gap-2">
                                <button 
                                  onClick={() => handleUserDecision('refined')} 
                                  className="flex-1 py-2 bg-amber-500 text-slate-900 text-[10px] font-black rounded-lg flex items-center justify-center gap-2 hover:bg-amber-400 transition-colors"
                                >
                                    <Send size={12}/> REFINE
                                </button>
                                <button 
                                  onClick={() => handleUserDecision('approved')} 
                                  className="flex-1 py-2 bg-slate-700 text-white text-[10px] font-black rounded-lg flex items-center justify-center gap-2 hover:bg-slate-600 transition-colors"
                                >
                                    <Check size={12}/> APPROVE
                                </button>
                            </div>
                          </div>
                        )}
                    </div>
                </div>
              </div>
            );
          })}
        </div>
      </NeumorphicCard>
    </div>
  );
};

export default ExecutionView;