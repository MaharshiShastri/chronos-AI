import React, { useState, useRef, useEffect } from 'react';
import { aiService } from '../services/api';
import { Send, Zap, Trash2, Clock, Edit2, Plus, ChevronLeft, Layout, MessageSquare, LogOut, Check, X } from 'lucide-react';
import NeumorphicCard from './NeumorphicCard';
import ExecutionView from './ExecutionView';

const ChatWindow = ({ onLogout }) => {
    // UI Navigation & State
    const [view, setView] = useState('chat'); // 'chat' or 'plan'
    const [activePlan, setActivePlan] = useState(null); 
    const [loading, setLoading] = useState(false);
    
    // Data States
    const [input, setInput] = useState('');
    const [messages, setMessages] = useState([]);
    const [conversations, setConversations] = useState([]);
    const [tasks, setTasks] = useState([]);

    // Edit States
    const [editingId, setEditingId] = useState(null);
    const [editTitle, setEditTitle] = useState('');

    // Plan Configuration
    const [timeBudget, setTimeBudget] = useState(600);
    const [planMode, setPlanMode] = useState('fast');

    const scrollRef = useRef(null);

    // 1. Initial Load: Archive and Task Log
    useEffect(() => {
        const initDashboard = async () => {
            try {
                const [convs, taskList] = await Promise.all([
                    aiService.getConversations(),
                    aiService.getTasks()
                ]);
                setConversations(convs.data || []);
                setTasks(taskList.data || []);
                
                const currentId = localStorage.getItem("current_conv_id");
                if (currentId) {
                    loadChatHistory(currentId);
                }
            } catch (err) {
                console.error("Initialization Error:", err);
            }
        };
        initDashboard();
    }, []);

    // 2. Scroll to Bottom
    useEffect(() => {
        scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // 3. Helper: Load Chat History
    const loadChatHistory = async (id) => {
        try {
            localStorage.setItem("current_conv_id", id);
            const res = await aiService.getChatHistory(id);
            setMessages(res.data || []);
            setView('chat');
        } catch (err) {
            console.error("History Load Error:", err);
        }
    };

    // 4. Chat Logic
    const handleChat = async () => {
        
        if (!input.trim() || loading) return;
        const currentInput = input;
        const currentId = localStorage.getItem("current_conv_id");
        
        setMessages(prev => [...prev, { role: 'user', content: currentInput }, { role: 'ai', content: '' }]);
        setInput('');
        setLoading(true);

        try {
            await aiService.streamChat(currentInput, currentId, (data) => {
                const token = data.token !== undefined ? data.token : data;
                setMessages(prev => {
                    const updated = [...prev];
                    updated[updated.length - 1].content += token;
                    return updated;
                });
            });
            const convs = await aiService.getConversations();
            setConversations(convs.data);
        } finally { setLoading(false); }
    };

    // 5. Plan Logic (With Normalization Fix)
    const handlePlanRequest = async () => {
    if (!input.trim() || loading) return;
    
    setLoading(true);
    // Keep activePlan null so we stay on the configuration screen with the loading spinner
    let firstStepReceived = false;

    try {
        // We await the entire execution of streamPlan
        await aiService.streamPlan(input, timeBudget, null, planMode, (data) => {
            console.log("Streamed Data:", data);
            if(data.token){
                if(!firstStepReceived){
                    firstStepReceived = true;
                    setActivePlan({
                        mission_id: Date.now(),
                        steps: []
                    });
                    setView('plan');
                }
            }
            if(data.enriched_step){
                setActivePlan(prev => ({
                    ...prev,
                    mission_id: data.mission_id,
                    steps: data.enriched_steps.map((s, idx) => ({
                        id: s.step_id || idx,
                        step: s.step,
                        time_allocated: parseInt(s.time_allocated || 60),
                    }))
                }));
            }
            if(data.error){
                throw new Error(data.error);
                console.log("Error in streamPlan:", data.error);
            }
    });
        const updatedTasks = await aiService.getTasks();
        setTasks(updatedTasks.data || []);
        
    } catch (err) {
        console.error("Stream Failure:", err);
        // Only alert if the stream finished and we still have no data
        if (!firstStepReceived) {
            alert("STRATEGIC_ERROR: Logic engine failed to provide a valid sequence.");
            setActivePlan(null);
            setView('plan'); 
        }
    } finally {
        setLoading(false);
    }
};
    // 6. Rename/Delete Handlers
    const startRename = (id, title, e) => {
        e.stopPropagation();
        setEditingId(id);
        setEditTitle(title || `Session_${id}`);
    };

    const confirmRename = async (id) => {
        if (!editTitle.trim()) return;
        await aiService.renameConversation(id, editTitle);
        setConversations(prev => prev.map(c => c.id === id ? { ...c, title: editTitle } : c));
        setEditingId(null);
    };

    const handleDelete = async (id, e) => {
        e.stopPropagation();
        if (window.confirm("Purge session?")) {
            await aiService.deleteConversation(id);
            setConversations(prev => prev.filter(c => c.id !== id));
            if (localStorage.getItem("current_conv_id") == id) {
                localStorage.removeItem("current_conv_id");
                setMessages([]);
            }
        }
    };

    return (
        <div className="flex gap-4 w-screen h-[90vh] px-6 py-4 overflow-hidden bg-[#0f172a] text-slate-300">
            
            {/* LEFT SIDEBAR: ARCHIVE */}
            <div className="w-64 flex flex-col gap-4">
                <div className="flex justify-between items-center px-2">
                    <h3 className="text-sky-500 text-[10px] font-black tracking-widest uppercase flex items-center gap-2">
                        <MessageSquare size={12}/> Archive_Index
                    </h3>
                    <Plus 
                        size={16} 
                        className="text-sky-400 cursor-pointer hover:rotate-90 transition-all" 
                        onClick={() => { localStorage.removeItem("current_conv_id"); setMessages([]); setView('chat'); }}
                    />
                </div>
                <div className="flex-1 overflow-y-auto space-y-2 custom-scrollbar pr-2">
                    {conversations.map(c => (
                        <div key={c.id} className="group relative">
                            {editingId === c.id ? (
                                <div className="flex items-center gap-1 bg-slate-800 p-2 rounded-xl border border-sky-500/30">
                                    <input autoFocus value={editTitle} onChange={(e) => setEditTitle(e.target.value)} className="bg-transparent text-[11px] outline-none w-full text-sky-400" />
                                    <Check size={12} className="text-green-500 cursor-pointer" onClick={() => confirmRename(c.id)} />
                                    <X size={12} className="text-red-500 cursor-pointer" onClick={() => setEditingId(null)} />
                                </div>
                            ) : (
                                <button 
                                    onClick={() => loadChatHistory(c.id)}
                                    className={`w-full text-left p-3 rounded-xl text-[11px] truncate transition-all pr-12 ${localStorage.getItem("current_conv_id") == c.id ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30 shadow-[0_0_10px_rgba(56,189,248,0.1)]' : 'text-slate-500 hover:bg-white/5 border border-transparent'}`}
                                >
                                    {c.title || `Session_${c.id}`}
                                </button>
                            )}
                            {editingId !== c.id && (
                                <div className="absolute right-3 top-3 hidden group-hover:flex gap-2 bg-[#1e293b]/80 backdrop-blur-sm pl-2">
                                    <Edit2 size={12} className="text-slate-400 hover:text-sky-400 cursor-pointer" onClick={(e) => startRename(c.id, c.title, e)} />
                                    <Trash2 size={12} className="text-slate-400 hover:text-red-500 cursor-pointer" onClick={(e) => handleDelete(c.id, e)} />
                                </div>
                            )}
                        </div>
                    ))}
                </div>
                <button onClick={onLogout} className="flex items-center gap-2 p-3 text-[10px] font-black text-slate-500 hover:text-red-400 transition-colors uppercase mt-auto border-t border-white/5 pt-4">
                    <LogOut size={14}/> Terminal_Exit
                </button>
            </div>

            {/* CENTER: PRIMARY WORKSPACE */}
            <div className="flex-1 flex flex-col gap-4">
                <div className="flex justify-center gap-4">
                    <button onClick={() => setView('chat')} className={`px-8 py-2 rounded-full text-[10px] font-black tracking-widest transition-all ${view === 'chat' ? 'bg-sky-500 text-slate-900 shadow-[0_0_15px_rgba(56,189,248,0.4)]' : 'text-slate-500'}`}>01_CHAT</button>
                    <button onClick={() => setView('plan')} className={`px-8 py-2 rounded-full text-[10px] font-black tracking-widest transition-all ${view === 'plan' ? 'bg-amber-500 text-slate-900 shadow-[0_0_15px_rgba(245,158,11,0.4)]' : 'text-slate-500'}`}>02_PLAN</button>
                </div>

                <NeumorphicCard className="flex-1 flex flex-col overflow-hidden p-6 relative">
                    {view === 'chat' ? (
                        <div className="flex flex-col h-full">
                            <div className="flex-1 overflow-y-auto space-y-6 mb-4 pr-2 custom-scrollbar">
                                {messages.length === 0 && (
                                    <div className="h-full flex flex-col items-center justify-center opacity-20 italic text-[10px] uppercase tracking-[0.3em]">Standby_For_Input</div>
                                )}
                                {messages.map((m, i) => (
                                    <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                        <div className={`max-w-[80%] p-4 rounded-2xl text-sm leading-relaxed ${m.role === 'user' ? 'bg-sky-600 text-white shadow-lg' : 'neumorphic-inset text-slate-300'}`}>
                                            {m.content}
                                        </div>
                                    </div>
                                ))}
                                <div ref={scrollRef} />
                            </div>
                            <div className="flex gap-3 mt-auto">
                                <input 
                                    value={input} 
                                    onChange={(e) => setInput(e.target.value)} 
                                    onKeyDown={(e) => e.key === 'Enter' && handleChat()} 
                                    placeholder="Inject parameters..." 
                                    className="flex-1 neumorphic-inset p-4 text-xs text-sky-400 outline-none placeholder:text-slate-700" 
                                />
                                <button onClick={handleChat} disabled={loading} className="p-4 bg-slate-800 rounded-xl hover:text-sky-400 transition-all active:scale-95 disabled:opacity-50">
                                    <Send size={20}/>
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="h-full overflow-y-auto custom-scrollbar">
                            {activePlan ? (
                                <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 h-full flex flex-col">
                                    <button 
                                        onClick={() => { setActivePlan(null); setLoading(false); }} 
                                        className="text-[10px] text-amber-500 flex items-center gap-1 mb-6 hover:text-amber-400 group transition-all w-fit"
                                    >
                                        <ChevronLeft size={14} className="group-hover:-translate-x-1 transition-transform"/> RECONFIGURE_PLAN
                                    </button>
                                    
                                    {/* SYNTHESIZING LOADER: Only shows if steps are empty AND we are still loading */}
                                    {activePlan.steps.length === 0 && loading ? (
                                        <div className="flex-1 flex flex-col items-center justify-center space-y-4">
                                            <div className="w-12 h-12 border-2 border-amber-500/10 border-t-amber-500 rounded-full animate-spin"></div>
                                            <div className="flex flex-col items-center gap-1">
                                                <p className="text-amber-500 text-[10px] font-black animate-pulse uppercase tracking-[0.2em]">
                                                    Synthesizing_Logic_Gates...
                                                </p>
                                                <p className="text-slate-600 text-[8px] font-mono">STREAMS_ACTIVE // GPU_LOAD: HIGH</p>
                                            </div>
                                        </div>
                                    ) : (
                                        <ExecutionView 
                                            plan={activePlan} 
                                            onComplete={() => { setActivePlan(null); setView('chat'); }} 
                                        />
                                    )}
                                </div>
                            ) : (
                                <div className="max-w-md mx-auto w-full pt-4 space-y-8">
                                    <div className="text-center">
                                        <h2 className="text-amber-500 font-black text-xl tracking-tighter">PLAN_ARCHITECT</h2>
                                        <p className="text-slate-600 text-[9px] uppercase tracking-widest mt-1">Logic_Constraint_Engine</p>
                                    </div>

                                    <div className="space-y-8">
                                        <div className="space-y-4">
                                            <div className="flex justify-between text-[10px] font-bold">
                                                <span className="text-slate-500 uppercase">Time_Budget</span>
                                                <span className="text-amber-400 font-mono">{timeBudget}s</span>
                                            </div>
                                            <input type="range" min="60" max="3600" step="60" value={timeBudget} onChange={(e) => setTimeBudget(e.target.value)} className="w-full h-1 bg-slate-800 rounded-lg appearance-none accent-amber-500 cursor-pointer" />
                                        </div>

                                        <div className="grid grid-cols-2 gap-4">
                                            <button onClick={() => setPlanMode('fast')} className={`py-4 rounded-xl text-[10px] font-black transition-all ${planMode === 'fast' ? 'bg-amber-500 text-slate-900 shadow-lg shadow-amber-900/40' : 'neumorphic-inset text-slate-500 opacity-50'}`}>FAST_MODE</button>
                                            <button onClick={() => setPlanMode('deep')} className={`py-4 rounded-xl text-[10px] font-black transition-all ${planMode === 'deep' ? 'bg-amber-500 text-slate-900 shadow-lg shadow-amber-900/40' : 'neumorphic-inset text-slate-500 opacity-50'}`}>DEEP_MODE</button>
                                        </div>

                                        <textarea 
                                            value={input} 
                                            onChange={(e) => setInput(e.target.value)} 
                                            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault() || handlePlanRequest())}
                                            placeholder="Define the objective..." 
                                            className="w-full h-32 neumorphic-inset p-4 text-xs text-amber-400 outline-none resize-none font-mono placeholder:text-slate-700" 
                                        />
                                        
                                        <button 
                                            onClick={handlePlanRequest} 
                                            disabled={loading || !input.trim()} 
                                            className="w-full py-4 bg-amber-500 rounded-xl text-slate-900 font-black flex items-center justify-center gap-3 hover:bg-amber-400 transition-all shadow-xl shadow-amber-900/20 active:scale-95 disabled:opacity-50"
                                        >
                                            {loading ? (
                                                <div className="flex items-center gap-2">
                                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-slate-900"></div>
                                                    <span>SYNTHESIZING...</span>
                                                </div>
                                            ) : (
                                                <><Zap size={18} fill="currentColor"/> INITIATE_DEPLOYMENT</>
                                            )}
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </NeumorphicCard>
            </div>

            {/* RIGHT SIDEBAR: OBJECTIVES */}
            <div className="w-72 flex flex-col gap-4">
                <h3 className="text-amber-500 text-[10px] font-black tracking-widest uppercase px-2 flex items-center gap-2">
                    <Layout size={12}/> Objectives_Log
                </h3>
                <div className="flex-1 overflow-y-auto space-y-4 custom-scrollbar pr-2">
                    {tasks.length === 0 ? (
                        <div className="text-[10px] text-slate-700 italic text-center mt-10 uppercase tracking-widest">Awaiting_Data</div>
                    ) : (
                        tasks.map(t => (
                            <div key={t.id} className="neumorphic-inset p-4 border border-white/5 transition-all hover:border-amber-500/20">
                                <div className="flex justify-between items-start mb-2 font-mono">
                                    <span className="text-[9px] text-slate-600">ID_{t.id}</span>
                                    <Clock size={12} className="text-amber-500"/>
                                </div>
                                <p className="text-[11px] text-slate-200 font-bold mb-3 uppercase tracking-tight">{t.title}</p>
                                <div className="flex items-center gap-3">
                                    <div className="flex-1 h-1 bg-slate-800 rounded-full overflow-hidden">
                                        <div className="h-full bg-amber-500 w-1/3"></div>
                                    </div>
                                    <span className="text-[9px] text-amber-500 font-mono">{t.total_time}s</span>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
};

export default ChatWindow;