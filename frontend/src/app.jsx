import React, {useEffect, useState} from 'react';
import ChatWindow from './components/ChatWindow';
import ExecutionView from './components/ExecutionView';
import {authService, aiService} from './services/api';
import AuthView from './components/AuthView';
import ShatterCube from './components/ShatterCube';

function App() {
    const [user, setUser] = useState(null);
    const [view, setView] = useState('auth');
    const [activePlan, setActivePlan] = useState([]);
    const [isTransitioning, setIsTransitioning] = useState(false); // NEW STATE
    const [pendingView, setPendingView] = useState(null);

    useEffect(() => {
        const token = localStorage.getItem('token');
        if(token){ triggerTransition('chat'); }
    }, []);

    const handleStartTask = (plan) => {
        setActivePlan(plan);
        setIsTransitioning(true); // Start the animation
    };

    const triggerTransition = (targetView, planData=null) => {
        if(planData) setActivePlan(planData);
        setPendingView(targetView);
        setIsTransitioning(true);
    }

    const onAnimationEnd = () => {
        console.log("Animation Ended. Moving to:", pendingView);
        if(pendingView) {
            setView(pendingView);
            setPendingView(null);
        } else {
            setPendingView('auth'); // Default to auth if something goes wrong
        }
        setIsTransitioning(false); // Remove cube
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        triggerTransition('auth');
    };

    return (
        <div className="min-h-screen w-full flex items-center justify-center bg-[#0f172a] overflow-hidden">
            
            {/* The Transition Layer: Higher z-index usually handled in CSS */}
            {isTransitioning && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0f172a]">
                    <ShatterCube onComplete={onAnimationEnd} />
                </div>
            )}

            {/* View Layer: Hidden during transition to prevent flicker */}
            {!isTransitioning && (
                <>
                    {view === 'auth' && (
                        <AuthView onAuthSuccess={() => triggerTransition('chat')} />
                    )}

                    {view === 'chat' && (
                        <ChatWindow 
                            onPlanGenerated={(plan) => triggerTransition('focus', plan)} 
                            onLogout={handleLogout} 
                        />
                    )}

                    {view === 'focus' && (
                        <ExecutionView 
                            plan={activePlan} 
                            onAbort={() => triggerTransition('chat')} 
                        />
                    )}
                </>
            )}
        </div>
    );
}

export default App;