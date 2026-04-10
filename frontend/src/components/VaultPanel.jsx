import React, { useState, useEffect } from 'react';
import { Shield, Plus, Trash2, X, Activity, Edit2, Check } from 'lucide-react';
import { aiService } from '../services/api';

const VaultPanel = () => {
    const [memories, setMemories] = useState([]); // This state stores your list
    const [editingId, setEditingId] = useState(null);
    const [editForm, setEditForm] = useState({
        fact_key: '',
        fact_value: '',
        importance: 3,
        category: 'Development'
    });
    const [formData, setFormData] = useState({
        fact_key: '',
        fact_value: '',
        importance: 3,
        category: 'Development'
    });

    const categories = ['Development', 'Hardware', 'Preference', 'Project_Goal', 'Personal', 'Constraint'];

    // Load memories on component mount
    useEffect(() => { 
        fetchMemories(); 
    }, []);

    const fetchMemories = async () => {
        try {
            const res = await aiService.getMemories();
            // axios wraps the response in a 'data' object
            // Ensure we set an empty array if the response is null/undefined
            setMemories(res.data || []); 
        } catch (err) { 
            console.error("Vault Load Error", err); 
        }
    };

    const handleSave = async (e) => {
        e.preventDefault();
        if (!formData.fact_key || !formData.fact_value) return;
        try {
            await aiService.addMemory(formData);
            // Reset form
            setFormData({ fact_key: '', fact_value: '', importance: 3, category: 'Development' });
            // Refresh local list
            fetchMemories();
        } catch (err) { 
            console.error("Vault Add Error", err); 
        }
    };
    
    const handleDelete = async (id) => {
        if (!window.confirm("PURGE_MEMORY: Confirm deletion?")) return;
        try {
            await aiService.deleteMemory(id);
            fetchMemories();
        } catch(err) {
            console.error("Vault Delete Error", err);
        }
    };

    const startEdit = (memory) => {
        setEditingId(memory.id);
        setEditForm({
            fact_key: memory.fact_key,
            fact_value: memory.fact_value,
            importance: memory.importance,
            category: memory.category
        });
    };

    const handleSaveEdit = async (memoryId) => {
        try {
            await aiService.updateMemory(memoryId, editForm);
            setEditingId(null);
            fetchMemories();
        } catch (err) {
            console.error("Vault Update Error", err);
        }
    };

    const cancelEdit = () => {
        setEditingId(null);
    };

    return (
        <div className="flex-1 flex flex-col max-w-5xl mx-auto w-full space-y-8 animate-in fade-in zoom-in-95 duration-500 pb-10">
            
            {/* FORM SECTION (ADD NEW MEMORY) */}
            <div className="p-8 rounded-[2rem] bg-[#1e1b4b]/20 border border-purple-500/20 backdrop-blur-xl shadow-[0_20px_50px_rgba(0,0,0,0.5)]">
                <div className="flex items-center gap-4 mb-8">
                    <div className="p-3 bg-purple-600 rounded-2xl shadow-[0_0_25px_rgba(147,51,234,0.4)]">
                        <Shield size={22} className="text-white" />
                    </div>
                    <div>
                        <h2 className="text-xl font-black tracking-widest text-white uppercase italic">Memory_Encoder</h2>
                        <p className="text-[10px] font-mono text-purple-400/60 uppercase tracking-[0.3em]">Inject Persistent Context</p>
                    </div>
                </div>

                <form onSubmit={handleSave} className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                        <div>
                            <label className="text-[10px] font-bold text-purple-400/80 ml-1 mb-2 block uppercase tracking-widest">Fact_Key</label>
                            <input 
                                value={formData.fact_key}
                                onChange={(e) => setFormData({...formData, fact_key: e.target.value})}
                                placeholder="e.g. TECH_STACK"
                                className="w-full bg-slate-950/50 border border-purple-500/20 rounded-xl py-3 px-4 text-sm text-white focus:border-purple-500 transition-all outline-none"
                            />
                        </div>
                        <div>
                            <label className="text-[10px] font-bold text-purple-400/80 ml-1 mb-2 block uppercase tracking-widest">Category</label>
                            <select 
                                value={formData.category}
                                onChange={(e) => setFormData({...formData, category: e.target.value})}
                                className="w-full bg-slate-950/50 border border-purple-500/20 rounded-xl py-3 px-4 text-sm text-white appearance-none focus:border-purple-500 transition-all outline-none"
                            >
                                {categories.map(c => <option key={c} value={c}>{c}</option>)}
                            </select>
                        </div>
                    </div>

                    <div className="space-y-4">
                        <div>
                            <label className="text-[10px] font-bold text-purple-400/80 ml-1 mb-2 block uppercase tracking-widest">Fact_Statement</label>
                            <textarea 
                                value={formData.fact_value}
                                onChange={(e) => setFormData({...formData, fact_value: e.target.value})}
                                placeholder="The specific detail you want the AI to remember..."
                                className="w-full bg-slate-950/50 border border-purple-500/20 rounded-xl py-3 px-4 text-sm text-white h-[115px] resize-none focus:border-purple-500 transition-all outline-none"
                            />
                        </div>
                    </div>

                    <div className="md:col-span-2 flex items-center justify-between bg-slate-950/30 p-4 rounded-2xl border border-purple-500/10">
                        <div className="flex-1 pr-10">
                            <label className="text-[10px] font-bold text-purple-400/80 ml-1 mb-4 block uppercase tracking-widest">
                                Importance_Weight: <span className="text-purple-400">{formData.importance}</span>
                            </label>
                            <input 
                                type="range" min="1" max="5" step="1"
                                value={formData.importance}
                                onChange={(e) => setFormData({...formData, importance: parseInt(e.target.value)})}
                                className="w-full h-1 bg-purple-900 rounded-lg appearance-none cursor-pointer accent-purple-500"
                            />
                        </div>
                        <button 
                            type="submit"
                            className="px-8 py-4 bg-purple-600 hover:bg-purple-500 text-white font-black text-xs rounded-xl transition-all shadow-[0_10px_20px_rgba(147,51,234,0.2)] flex items-center gap-3 active:scale-95"
                        >
                            <Plus size={16} />
                            COMMIT_TO_VAULT
                        </button>
                    </div>
                </form>
            </div>

            {/* GRID OF MEMORIES */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 overflow-y-auto custom-scrollbar pr-2">
                {memories.map((m) => {
                    const isEditing = editingId === m.id;
                    return (
                        <div key={m.id} className={`group relative p-6 rounded-3xl bg-[#0f172a]/40 border ${isEditing ? 'border-purple-500 shadow-[0_0_20px_rgba(168,85,247,0.15)]' : 'border-slate-800/60'} hover:border-purple-500/50 transition-all duration-300`}>
                            {isEditing ? (
                                <div className="space-y-4 animate-in fade-in zoom-in-95 duration-200">
                                    <div className="flex justify-between items-center gap-2">
                                        <input 
                                            value={editForm.fact_key}
                                            onChange={(e) => setEditForm({...editForm, fact_key: e.target.value})}
                                            className="w-1/2 bg-slate-950/50 border border-purple-500/30 rounded-lg py-1.5 px-3 text-xs text-white outline-none focus:border-purple-500"
                                        />
                                        <select 
                                            value={editForm.category}
                                            onChange={(e) => setEditForm({...editForm, category: e.target.value})}
                                            className="bg-slate-950/50 border border-purple-500/30 rounded-lg py-1.5 px-3 text-xs text-white outline-none focus:border-purple-500"
                                        >
                                            {categories.map(c => <option key={c} value={c}>{c}</option>)}
                                        </select>
                                    </div>
                                    <textarea 
                                        value={editForm.fact_value}
                                        onChange={(e) => setEditForm({...editForm, fact_value: e.target.value})}
                                        className="w-full bg-slate-950/50 border border-purple-500/30 rounded-xl py-3 px-4 text-xs text-white h-[80px] resize-none outline-none focus:border-purple-500"
                                    />
                                    <div className="flex justify-end gap-2 pt-2 border-t border-slate-800/50">
                                        <button onClick={cancelEdit} className="p-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-400 transition-colors">
                                            <X size={14} />
                                        </button>
                                        <button onClick={() => handleSaveEdit(m.id)} className="p-2 bg-purple-600 hover:bg-purple-500 rounded-lg text-white transition-all shadow-lg shadow-purple-500/20">
                                            <Check size={14} />
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <>
                                    <div className="flex justify-between items-start mb-4">
                                        <div className="space-y-1">
                                            <span className="text-[9px] font-black text-purple-500 uppercase tracking-widest">{m.category}</span>
                                            <h3 className="text-sm font-black text-white uppercase tracking-tight">{m.fact_key}</h3>
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <div className="flex gap-0.5 mr-2">
                                                {[...Array(5)].map((_, i) => (
                                                    <div key={i} className={`w-1.5 h-1.5 rounded-full ${i < m.importance ? 'bg-purple-500' : 'bg-slate-800'}`} />
                                                ))}
                                            </div>
                                            <button onClick={() => startEdit(m)} className="p-1.5 text-slate-600 hover:text-purple-400 transition-colors opacity-0 group-hover:opacity-100">
                                                <Edit2 size={13} />
                                            </button>
                                            <button onClick={() => handleDelete(m.id)} className="p-1.5 text-slate-600 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100">
                                                <Trash2 size={13} />
                                            </button>
                                        </div>
                                    </div>
                                    <p className="text-xs text-slate-400 leading-relaxed font-medium">"{m.fact_value}"</p>
                                    <div className="mt-6 pt-4 border-t border-slate-800/50 flex justify-between items-center">
                                        <span className="text-[8px] font-mono text-slate-700 tracking-widest uppercase">ID_REF_{m.id}</span>
                                        <Activity size={12} className="text-purple-900" />
                                    </div>
                                </>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default VaultPanel;