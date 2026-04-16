import React, { useState, useRef, useEffect } from 'react';
import { aiService } from '../services/api';
import { Zap, Trash2, Clock, Target, MessageSquare } from 'lucide-react';
import VaultPanel from './VaultPanel';
import ChatPanel from './ChatPanel';
import PlanPanel from './PlanPanel';
import Sidebar from './Sidebar';

const ChatWindow = ({ onLogout}) => {
    // UI Navigation & State
    const [view, setView] = useState('chat'); // 'chat' or 'plan'
    const [activePlan, setActivePlan] = useState(null); 
    const [loading, setLoading] = useState(false);
    const [memories, setMemories] = useState([]);
    // Data States
    const [input, setInput] = useState('');
    const [messages, setMessages] = useState([]);
    const [conversations, setConversations] = useState([]);
    const [tasks, setTasks] = useState([]);

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
        
        // Optimistic UI update
        setMessages(prev => [...prev, { role: 'user', content: currentInput }, { role: 'ai', content: '' }]);
        setInput('');
        setLoading(true);

        try {
            await aiService.streamChat(currentInput, currentId, (data) => {
                if (data.conversation_id) {
                    localStorage.setItem("current_conv_id", data.conversation_id);
                    return; // Don't append the ID to the message content
                }
                const token = data.token !== undefined ? data.token : data;
                setMessages(prev => {
                    const updated = [...prev];
                    const lastMsg = updated[updated.length - 1];
                    updated[updated.length - 1] = { ...lastMsg, content: lastMsg.content + token };
                    return updated;
                });
            });
            // Refresh conversation list to show new titles/updates
            const convs = await aiService.getConversations();
            setConversations(convs.data || []);
        } catch (err) {
            console.error("Chat Error:", err);
        } finally { 
            setLoading(false); 
        }
    };
    const fetchMemories = async () => {
    const data = await aiService.getMemories();
    setMemories(data);
};
useEffect(() => { fetchMemories(); }, []);
    // 5. Plan Logic 
    const handlePlanRequest = async () => {
    if (!input.trim() || loading) return;
    
    setLoading(true);
    // Initialize with empty steps
    setActivePlan({ mission_id: null, steps: [] });
    setView('plan');
    
    let planReceived = false;
    try {
        await aiService.streamPlan(input, timeBudget, null, planMode, (data) => {
            // A. Handle individual streaming steps
            if (data.single_step) {
                setActivePlan(prev => ({
                    ...prev,
                    steps: [...prev.steps, {
                        id: `temp-${prev.steps.length}`,
                        // Use .step OR .description to be safe
                        description: data.single_step.step || data.single_step.description,
                        time_allocated: parseInt(data.single_step.time_allocated || 60),
                    }]
                }));
            }

            // B. Handle the final "complete" payload from DB
            if (data.status === 'complete' && data.enriched_steps) {
                planReceived = true;
                setActivePlan({
                    mission_id: data.mission_id,
                    steps: data.enriched_steps.map((s) => ({
                        id: s.backend_step_id,
                        description: s.description, // Matches task_service.py
                        time_allocated: parseInt(s.time_allocated || 60),
                    }))
                });
                setLoading(false); // Stop loading once DB sync is done
            }

            if (data.error) throw new Error(data.error);
        });

        const updatedTasks = await aiService.getTasks();
        setTasks(updatedTasks.data || []);
    } catch (err) {
        console.error("Plan Error:", err);
        if (!planReceived) {
            alert("STRATEGIC_ERROR: Logic engine failed.");
            setActivePlan(null);
        }
    } finally {
        setLoading(false);
    }
};

    // 6. Archive Management (Sessions)
    const startRename = async (id, currentTitle, e) => {
        if (e) e.stopPropagation();
        const newTitle = window.prompt("RENAME_SESSION:", currentTitle || `Session_${id}`);
        
        if (newTitle && newTitle.trim() !== "") {
            try {
                await aiService.renameConversation(id, newTitle.trim()); 
                setConversations(prev => prev.map(c => 
                    c.id === id ? { ...c, title: newTitle.trim() } : c
                ));
            } catch (err) {
                console.error("Rename Failed:", err);
            }
        }
    };

    const handleDelete = async (id, e) => {
        if (e) e.stopPropagation();
        if (window.confirm("PURGE_SESSION: Are you sure?")) {
            try {
                await aiService.deleteConversation(id);
                setConversations(prev => prev.filter(c => c.id !== id));
                if (localStorage.getItem("current_conv_id") == id) {
                    localStorage.removeItem("current_conv_id");
                    setMessages([]);
                }
            } catch (err) {
                console.error("Delete Failed:", err);
            }
        }
    };

    // 7. Objective Log Management (Tasks)
    const handleDeleteTask = async (id, e) => {
        if (e) e.stopPropagation();
        if (window.confirm("DELETE_OBJECTIVE: Permanent removal?")) {
            try {
                await aiService.deleteTask(id);
                setTasks(prev => prev.filter(t => t.id !== id));
            } catch (err) {
                console.error("Task deletion failed");
            }
        }
    };

    //8. New Chat Session
    const handleNewChat = () =>{
        localStorage.removeItem("current_conv_id");

        setMessages([]);
        setView('chat');
        setInput('');

        console.log("New chat session initialized");
    }

    const handleMasterInput = async() => {
        if(!input.trim() || loading) return;

        setLoading(true);
        const userQuery = input;

        try{
            const isPlanQuery = /plan|steps|schedule|how to|build|create/i.test(userQuery);

            if(isPlanQuery){
                setView('plan');
                await handlePlanRequest();
            }
            else{
                setView('chat');
                await handleChat();
            }
        } catch(err){
            console.error("Routing error:", err);
        } finally{
            setLoading(false);
        }
    };
    
    return (
        <div className="flex h-screen bg-[#0a0f1a] text-white font-sans overflow-hidden">
            
            {/* COLUMN 1: ARCHIVE_INDEX */}
            <Sidebar 
                conversations={conversations}
                activeId={localStorage.getItem("current_conv_id")}
                onSelectConv={loadChatHistory}
                onLogout={onLogout}
                onRename={startRename}
                onDelete={handleDelete}
                onNewChat={handleNewChat}
            />

            {/* COLUMN 2: MAIN PANEL */}
            <main className="flex-[2] flex flex-col relative overflow-hidden border-x border-slate-800/40 bg-[#0f172a]/30 transition-all duration-700 ease-in-out">
                
                {/* NAVIGATION TABS */}
                <div className="flex justify-center items-center py-6 gap-4 z-50">
                    <button 
                        onClick={() => setView('chat')}
                        className={`flex items-center gap-2 px-6 py-2 rounded-full border transition-all duration-300 ${
                            view === 'chat' 
                            ? 'bg-cyan-500 text-black border-cyan-400 shadow-[0_0_20px_rgba(6,182,212,0.3)]' 
                            : 'bg-slate-900/50 text-slate-500 border-slate-800 hover:text-slate-300'
                        }`}
                    >
                        <MessageSquare size={14} fill={view === 'chat' ? "currentColor" : "none"} />
                        <span className="text-[10px] font-black tracking-[0.2em] uppercase">01_CHAT</span>
                    </button>

                    <button 
                        onClick={() => setView('plan')}
                        className={`flex items-center gap-2 px-6 py-2 rounded-full border transition-all duration-300 ${
                            view === 'plan' 
                            ? 'bg-orange-500 text-black border-orange-400 shadow-[0_0_20px_rgba(249,115,22,0.3)]' 
                            : 'bg-slate-900/50 text-slate-500 border-slate-800 hover:text-slate-300'
                        }`}
                    >
                        <Zap size={14} fill={view === 'plan' ? "currentColor" : "none"} />
                        <span className="text-[10px] font-black tracking-[0.2em] uppercase">02_PLAN</span>
                    </button>
                    <button 
                        onClick={() => setView('vault')}
                        className={`flex items-center gap-2 px-6 py-2 rounded-full border transition-all ${
                            view === 'vault' ? 'bg-purple-500 text-black border-purple-400 ' : 'bg-slate-900/50 text-slate-500 border-slate-800 hover:text-slate-300'
                        }`}
                    >
                        <Clock size={14} />
                        <span className="text-[10px] font-black tracking-[0.2em] uppercase">03_VAULT</span>
                    </button>
                </div>

                {/* CONTENT AREA */}
                <div className="flex-1 flex flex-col overflow-hidden transition-all duration-500 px-4 pb-4">
                    {view === 'chat' ? (
                        <ChatPanel 
                            messages={messages} 
                            input={input}
                            setInput={setInput} 
                            onSend={handleMasterInput}
                            loading={loading}
                            scrollRef={scrollRef}
                            memories={memories} 
                            onMemoryChange={fetchMemories}
                        />
                    ) : view === 'plan' ? (
                        <PlanPanel 
                            activePlan={activePlan} 
                            loading={loading}
                            timeBudget={timeBudget}
                            setTimeBudget={setTimeBudget}
                            planMode={planMode}
                            setPlanMode={setPlanMode}
                            onBack={() => setView('chat')}
                            onRequestPlan={handleMasterInput}
                            onCompleteExecution={() => setActivePlan(null)} // Returns to original PlanPanel
                            input={input}
                            setInput={setInput}
                        />
                    ) : <VaultPanel />}
                </div>
            </main>

            {/* COLUMN 3: OBJECTIVES_LOG */}
            <aside className="w-80 h-full p-6 flex flex-col bg-[#0a0f1a] transition-all duration-500 ease-in-out">
                <div className="flex items-center gap-2 mb-8 px-2">
                    <Target size={14} className="text-orange-500" />
                    <h2 className="text-[10px] font-black text-slate-500 tracking-[0.2em] uppercase">Objectives_Log</h2>
                </div>

                <div className="flex-1 space-y-4 overflow-y-auto pr-2 custom-scrollbar">
                    {tasks.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center opacity-20">
                            <Zap size={32} />
                            <p className="text-[8px] font-mono tracking-widest mt-2">IDLE_STATE</p>
                        </div>
                    ) : (
                        tasks.map(t => (
                            <div 
                                key={t.id} 
                                className="group p-4 rounded-xl bg-slate-900/40 border border-slate-800/60 hover:border-orange-500/30 transition-all duration-300 relative"
                            >
                                <div className="flex justify-between items-center mb-3">
                                    <span className="text-[8px] font-mono text-slate-600 uppercase tracking-tighter">
                                        ID_{t.id.toString().slice(-2)}
                                    </span>
                                    <div className="flex gap-2">
                                        <button 
                                            onClick={(e) => handleDeleteTask(t.id, e)}
                                            className="opacity-0 group-hover:opacity-100 p-1 text-slate-600 hover:text-red-500 transition-all"
                                        >
                                            <Trash2 size={12} />
                                        </button>
                                        <Clock size={12} className="text-orange-500/40" />
                                    </div>
                                </div>
                                
                                <p className="text-[11px] font-black uppercase tracking-tight text-slate-300 leading-tight mb-4 group-hover:text-white">
                                    {t.title}
                                </p>
                                
                                <div className="h-1 w-full bg-slate-950 rounded-full overflow-hidden">
                                    <div 
                                        className="h-full bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.5)] transition-all duration-1000" 
                                        style={{ width: t.status === 'completed' ? '100%' : '40%' }}
                                    />
                                </div>
                                <div className="flex justify-between mt-2">
                                    <span className="text-[8px] font-mono text-slate-700">{timeBudget}S</span>
                                    <span className="text-[8px] font-mono text-slate-700 uppercase">{t.status || 'running'}</span>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </aside>
        </div>
    );
};

export default ChatWindow;
