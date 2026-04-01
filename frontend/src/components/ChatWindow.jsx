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
    setActivePlan({mission_id: null, steps: []});
    setView('plan');
    
    let planReceived = false;
    try {
        // We await the entire execution of streamPlan
        await aiService.streamPlan(input, timeBudget, null, planMode, (data) => {
            console.log("Streamed Data:", data);
            if(data.enriched_steps && data.enriched_steps.length > 0){
                planReceived = true;
                setActivePlan({
                    mission_id: data.mission_id,
                    steps: data.enriched_steps.map((s, idx) => ({
                        id: s.step_id || idx,
                        step: s.step,
                        time_allocated: parseInt(s.time_allocated || 60),
                    }))
                });
            }
            if(data.error){
                console.log("Error in streamPlan:", data.error);
                setActivePlan(null);
                throw new Error(data.error);
            }
    });
    const updatedTasks = await aiService.getTasks();
    setTasks(updatedTasks.data || []);
        
    } catch (err) {
        console.error("Stream Failure:", err);
        // Only alert if the stream finished and we still have no data
        if (!planReceived) {
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

    const handleDeleteTask = async(id, e) => {
        e.stopPropagation();
        if(window.confirm("Delete this objecctive log?")){
            try{
                await aiService.deleteTask(id);
                setTasks(prev => prev.filter(t => t.id !== id));
            } catch(err){
                console.error("Unable to delete task!");
            }
        }
    };

    return (
    <div className="flex h-screen bg-slate-950 text-white font-sans overflow-hidden">
        {/* SIDEBAR: Passes task and conversation lists */}
        <Sidebar 
            conversations={conversations}
            tasks={tasks}
            activeId={localStorage.getItem("current_conv_id")}
            onSelectConv={loadChatHistory}
            onDeleteConv={handleDelete}
            onDeleteTask={handleDeleteTask}
            onLogout={onLogout}
        />
        
        <main className="flex-1 flex flex-col relative overflow-hidden">
            {/* VIEW SWITCHER */}
            {view === 'chat' ? (
                <ChatPanel 
                    messages={messages} 
                    input={input}
                    setInput={setInput} 
                    onSend={handleChat}
                    loading={loading}
                    scrollRef={scrollRef}
                />
            ) : (
                <PlanPanel 
                    activePlan={activePlan} 
                    loading={loading}
                    timeBudget={timeBudget}
                    setTimeBudget={setTimeBudget}
                    planMode={planMode}
                    setPlanMode={setPlanMode}
                    onBack={() => setView('chat')}
                    onRequestPlan={handlePlanRequest}
                />
            )}
        </main>
    </div>
);
};

export default ChatWindow;