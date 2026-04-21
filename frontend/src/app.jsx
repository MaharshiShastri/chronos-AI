import React, {useEffect, useState} from 'react';
import ChatWindow from './components/ChatWindow';
import ExecutionView from './components/ExecutionView';
import {authService, aiService} from './services/api';
import AuthView from './components/AuthView';
import ShatterCube from './components/ShatterCube';
import Dashboard from './components/Dashboard';
function App() {
    const [user, setUser] = useState(null);
    const [view, setView] = useState('auth');
    const [activePlan, setActivePlan] = useState([]);
    const [isTransitioning, setIsTransitioning] = useState(false); // NEW STATE
    const [pendingView, setPendingView] = useState(null);

    useEffect(() => {
        const token = localStorage.getItem('token');
        if(token){ triggerTransition('dashboard'); }
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
        if(pendingView) {
            setView(pendingView);
            setPendingView(null);
        } else {
            setPendingView('auth'); // Default to auth if something goes wrong
        }
        setIsTransitioning(false); // Remove cube
    };

    const handleLogout = () => {
        localStorage.clear();
        triggerTransition('auth');
    };

    return (
        <div className="min-h-screen w-full flex items-center justify-center bg-[#0f172a] overflow-hidden">
            
            {/* Transition Overlay */}
            {isTransitioning && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0f172a]">
                    <ShatterCube onComplete={onAnimationEnd} />
                </div>
            )}

            {/* Main Content */}
            {!isTransitioning && (
                <>
                    {view === 'auth' && (
                        <AuthView onAuthSuccess={() => triggerTransition('dashboard')} />
                    )}

                    {/* KPI/Dashboard as the Home Base */}
                    {view === 'dashboard' && (
                        <div className="w-full h-full relative">
                            <Dashboard />
                            {/* Floating Action Button to enter Chat */}
                            <button 
                                onClick={() => triggerTransition('chat')}
                                className="fixed bottom-8 right-8 bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-full shadow-lg font-bold transition-all hover:scale-105"
                            >
                                Start New Mission
                            </button>
                        </div>
                    )}

                    {view === 'chat' && (
                        <ChatWindow 
                            onPlanGenerated={(plan) => triggerTransition('focus', plan)} 
                            onLogout={handleLogout}
                            onBack={() => triggerTransition('dashboard')} // Added back navigation
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
