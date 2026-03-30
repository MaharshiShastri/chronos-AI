import React from 'react';

const NeumorphicCard = ({ children, className = "", title = "" }) => {
    return (
        <div className={`neumorphic-card ${className} p-8`}>
            {title && (
                <div className="flex items-center gap-3 mb-6 border-b border-white/10 pb-4">
                    <div className="w-3 h-3 rounded-full bg-sky-500 shadow-[0_0_10px_#38bdf8]"></div>
                    <h2 className="text-sky-400 font-bold tracking-[0.2em] text-sm">{title}</h2>
                </div>
            )}
            <div className="w-full h-full">
                {children}
            </div>
        </div>
    );
};

export default NeumorphicCard;