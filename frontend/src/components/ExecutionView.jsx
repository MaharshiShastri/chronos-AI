import React, { useState, useMemo, useEffect } from 'react';
import NeumorphicCard from './NeumorphicCard';
import { CheckCircle2, Circle, Play, ArrowRight, ChevronLeft, Timer, AlertCircle } from 'lucide-react';

const ExecutionView = ({ plan, onComplete }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const[timeLeft, setTimeLeft] = useState(0);
  const [isPaused, setIsPaused] = useState(false);

  // 1. ROBUST DATA NORMALIZATION
  const steps = useMemo(() => {
    console.log("ExecutionView received plan:", plan);
    if (!plan) return [];
    
    // 1. If it's already an array, use it
    if (Array.isArray(plan)) return plan;
    
    // 2. If it's an object with a 'steps' array, use that
    if (plan.steps && Array.isArray(plan.steps)) return plan.steps;
    
    // 3. Fallback: If it's a single object that looks like a step, wrap it
    if (plan.step || plan.description) return [plan];

    return [];
}, [plan]);

  useEffect(() => {
    if(steps[currentStep]){
      setTimeLeft(steps[currentStep].time_allocated || 60);
    }
  }, [currentStep, steps]);

  useEffect(() => {
    if(timeLeft <= 0 || isPaused) return;

    const timer = setInterval(() => {
      setTimeLeft(prev => prev > 0 ? prev - 1 : 0);
    }, 1000);

    return () => clearInterval(timer);
  }, [timeLeft, isPaused]);

  if (steps.length === 0) {
    return (
      <div className="text-center p-10 neumorphic-card text-red-400 font-mono border-red-500/20">
        CRITICAL_ERROR: NO_STEPS_LOADED
      </div>
    );
  }

  const progress = ((currentStep + 1) / steps.length) * 100;

  return (
    <div className="w-full max-w-2xl mx-auto space-y-6">
      
      {/* HEADER: GLOBAL MISSION STATUS */}
      <div className="flex justify-between items-end px-2">
        <div className="space-y-1">
          <span className="text-[10px] text-sky-500 font-black tracking-widest uppercase">Mission_Timeline</span>
          <div className="flex items-center gap-3">
             <Timer size={18} className={timeLeft < 10 ? "text-red-500 animate-pulse" : "text-sky-400"} />
             <span className={`text-2xl font-mono font-black ${timeLeft < 10 ? "text-red-500" : "text-white"}`}>
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
          {steps.map((step, index) => {
            const isActive = index === currentStep;
            const isCompleted = index < currentStep;
            const isTimeout = isActive && timeLeft === 0;
            
            return (
              <div 
                key={step.task_id || index} 
                className={`flex items-start gap-5 p-5 rounded-2xl transition-all duration-500 border ${
                  isActive 
                    ? 'bg-sky-500/5 border-sky-500/30 scale-[1.02] shadow-xl shadow-sky-900/20' 
                    : 'border-transparent opacity-30'
                }`}
              >
                {/* ICON BLOCK */}
                <div className="mt-1 flex-shrink-0">
                  {isCompleted ? (
                    <CheckCircle2 className="text-sky-500" size={22} />
                  ) : isActive ? (
                    <div className={`rounded-full p-1 shadow-lg ${isTimeout ? 'bg-red-500 animate-bounce' : 'bg-sky-500 shadow-sky-500/50'}`}>
                       {isTimeout ? <AlertCircle size={14} className="text-white"/> : <Play className="text-slate-900" size={14} fill="currentColor" />}
                    </div>
                  ) : (
                    <Circle className="text-slate-700" size={22} />
                  )}
                </div>
                
                {/* CONTENT BLOCK */}
                <div className="flex-1 space-y-1">
                  <div className="flex justify-between items-center">
                    <p className={`font-mono text-[9px] uppercase font-black ${isActive ? 'text-sky-400' : 'text-slate-600'}`}>
                      PHASE_{index + 1} <span className="ml-2 opacity-50">[{step.task_id || 'N/A'}]</span>
                    </p>
                    {/* TASK 1: Time allocated at flex-end */}
                    <p className={`text-[10px] font-mono ${isActive ? 'text-sky-400' : 'text-slate-600'}`}>
                      ALLOCATED: {step.time_allocated}s
                    </p>
                  </div>
                  <p className={`text-sm leading-relaxed ${isActive ? 'text-white' : 'text-slate-500'}`}>
                    {step.step || step.description || "Undefined Directive"}
                  </p>
                </div>
              </div>
            );
          })}

          {/* CONTROLS */}
          <div className="mt-8 pt-6 border-t border-white/5 flex justify-between items-center">
            <button 
              onClick={() => setCurrentStep(prev => Math.max(0, prev - 1))}
              disabled={currentStep === 0}
              className="flex items-center gap-2 text-slate-500 hover:text-white transition-colors text-[10px] font-black uppercase disabled:opacity-0"
            >
              <ChevronLeft size={14} /> Previous
            </button>

            <div className="flex gap-4">
               <button 
                onClick={() => setIsPaused(!isPaused)}
                className="px-4 py-2 rounded-lg border border-white/10 text-[10px] font-black uppercase text-slate-400 hover:bg-white/5"
               >
                 {isPaused ? 'Resume' : 'Pause'}
               </button>

               <button 
                onClick={() => {
                  if (currentStep < steps.length - 1) {
                    setCurrentStep(prev => prev + 1);
                  } else {
                    onComplete();
                  }
                }}
                className={`px-8 py-3 rounded-xl font-black text-xs flex items-center gap-3 transition-all active:scale-95 shadow-lg ${
                    timeLeft === 0 ? 'bg-red-500 text-white shadow-red-900/20' : 'bg-sky-500 text-slate-900 shadow-sky-900/20'
                }`}
              >
                {currentStep === steps.length - 1 ? 'FINAL_COMPLETE' : 'NEXT_PHASE'}
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </div>
      </NeumorphicCard>
    </div>
  );
};

export default ExecutionView;