import React, { useState } from 'react';
import { Upload, FileText, CheckCircle, Loader2 } from 'lucide-react';
import { aiService } from '../services/api';

const UploadPanel = () => {
    const [file, setFile] = useState(null);
    const [status, setStatus] = useState('idle'); // idle, uploading, success, error

    const handleUpload = async () => {
        if (!file) return;
        setStatus('uploading');
        try {
            await aiService.uploadDocument(file);
            setStatus('success');
            setFile(null);
            // Optional: trigger a refresh of a document list here
        } catch (err) {
            console.error("Upload Failed", err);
            setStatus('error');
        }
    };

    return (
        <div className="p-8 rounded-[2rem] bg-[#1e1b4b]/20 border border-purple-500/20 backdrop-blur-xl shadow-2xl">
            <div className="flex items-center gap-4 mb-8">
                <div className="p-3 bg-indigo-600 rounded-2xl">
                    <Upload size={22} className="text-white" />
                </div>
                <div>
                    <h2 className="text-xl font-black tracking-widest text-white uppercase italic">Knowledge_Ingestor</h2>
                    <p className="text-[10px] font-mono text-indigo-400/60 uppercase tracking-[0.3em]">Vectorize External PDFs</p>
                </div>
            </div>

            <div className={`relative border-2 border-dashed rounded-3xl p-12 transition-all duration-500 flex flex-col items-center justify-center 
                ${status === 'uploading' ? 'border-indigo-500 bg-indigo-500/10' : 'border-slate-800 hover:border-indigo-500/50 bg-slate-950/20'}`}>
                
                <input 
                    type="file" 
                    accept=".pdf"
                    onChange={(e) => setFile(e.target.files[0])}
                    className="absolute inset-0 opacity-0 cursor-pointer"
                />

                {status === 'idle' && (
                    <>
                        <FileText size={48} className="text-slate-700 mb-4" />
                        <p className="text-sm text-slate-400 font-medium">
                            {file ? file.name : "Drop PDF here or click to browse"}
                        </p>
                    </>
                )}

                {status === 'uploading' && (
                    <div className="flex flex-col items-center">
                        <Loader2 size={48} className="text-indigo-500 animate-spin mb-4" />
                        <p className="text-sm text-indigo-400 font-black animate-pulse uppercase tracking-tighter">Chunking & Embedding...</p>
                    </div>
                )}

                {status === 'success' && (
                    <div className="flex flex-col items-center animate-in zoom-in">
                        <CheckCircle size={48} className="text-emerald-500 mb-4" />
                        <p className="text-sm text-emerald-400 font-bold uppercase">Document Encoded to FAISS</p>
                        <button onClick={() => setStatus('idle')} className="mt-4 text-[10px] text-slate-500 underline uppercase tracking-widest">Upload Another</button>
                    </div>
                )}
            </div>

            {file && status === 'idle' && (
                <button 
                    onClick={handleUpload}
                    className="w-full mt-6 py-4 bg-indigo-600 hover:bg-indigo-500 text-white font-black text-xs rounded-xl transition-all shadow-lg shadow-indigo-500/20 active:scale-95"
                >
                    START_INGESTION_SEQUENCE
                </button>
            )}
        </div>
    );
};

export default UploadPanel;