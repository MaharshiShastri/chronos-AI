import React, { useState, useMemo } from 'react';
import NeumorphicCard from './NeumorphicCard';
import { CheckCircle2, Circle, Play, ArrowRight, ChevronLeft, Timer, AlertCircle } from 'lucide-react';

const ExecutionView = ({ plan, onComplete }) => {
  const [currentStep, setCurrentStep] = useState(0);
  //const[currentTime, setCurrentTime] = useState(0);
  //const [isPaused, setIsPaused] = useState(false);

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
      {/* 2. PROGRESS TRACKER */}
      <div className="px-2 space-y-2">
        <div className="flex justify-between text-[10px] font-black text-sky-500 uppercase tracking-widest">
          <span>Mission_Progress</span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div className="h-1.5 w-full bg-slate-900 rounded-full overflow-hidden border border-white/5">
          <div 
            className="h-full bg-sky-500 transition-all duration-700 shadow-[0_0_15px_#38bdf8]" 
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      <NeumorphicCard title="MISSION_EXECUTION" className="w-full">
        <div className="space-y-4">
          {steps.map((step, index) => {
            const isActive = index === currentStep;
            const isCompleted = index < currentStep;
            
            return (
              <div 
                key={index} 
                className={`flex items-start gap-5 p-5 rounded-2xl transition-all duration-500 border ${
                  isActive 
                    ? 'bg-sky-500/5 border-sky-500/30 scale-[1.02] shadow-lg shadow-sky-900/10' 
                    : 'border-transparent opacity-40'
                }`}
              >
                <div className="mt-1 flex-shrink-0">
                  {isCompleted ? (
                    <CheckCircle2 className="text-sky-500" size={22} />
                  ) : isActive ? (
                    <div className="bg-sky-500 rounded-full p-1 shadow-[0_0_15px_rgba(56,189,248,0.5)]">
                       <Play className="text-slate-900" size={14} fill="currentColor" />
                    </div>
                  ) : (
                    <Circle className="text-slate-700" size={22} />
                  )}
                </div>
                
                <div className="flex-1 space-y-1">
                  <p className={`font-mono text-xs uppercase font-black ${isActive ? 'text-sky-400' : 'text-slate-600'}`}>
                    Phase_{index + 1}
                  </p>
                  <p className={`text-sm leading-relaxed ${isActive ? 'text-white' : 'text-slate-500'}`}>
                    {typeof step === 'string' ? step : (step.step || step.description || step.task || "Undefined Step")}
                  </p>
                </div>
              </div>
            );
          })}

          <div className="mt-8 pt-6 border-t border-white/5 flex justify-between items-center px-2">
            <button 
              onClick={() => setCurrentStep(prev => Math.max(0, prev - 1))}
              disabled={currentStep === 0}
              className="flex items-center gap-2 text-slate-500 hover:text-white transition-colors text-[10px] font-black uppercase tracking-tighter disabled:opacity-0"
            >
              <ChevronLeft size={14} /> Back
            </button>
            
            <button 
              onClick={() => {
                // FIXED: Use 'steps.length' instead of 'plan.steps.length'
                if (currentStep < steps.length - 1) {
                  setCurrentStep(prev => prev + 1);
                } else {
                  onComplete();
                }
              }}
              className="bg-sky-500 text-slate-900 px-8 py-3 rounded-xl font-black text-xs flex items-center gap-3 hover:bg-sky-400 transition-all shadow-lg shadow-sky-900/20 active:scale-95"
            >
              {currentStep === steps.length - 1 ? 'COMPLETE_MISSION' : 'PROCEED_TO_NEXT'}
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </NeumorphicCard>
    </div>
  );
};

export default ExecutionView;