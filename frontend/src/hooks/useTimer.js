import { useState, useEffect } from "react";
export const useTimer = (initialSeconds, onComplete) => {
    const [timeLeft, setTimeLeft] = useState(initialSeconds);
    const [isActive, setIsActive] = useState(false);

    useEffect(() => {
        let interval = null;
        if(isActive && timeLeft > 0){
            interval = setInterval(() => {
                setTimeLeft((prev) => prev - 1);
            }, 1000);
        } else if(timeLeft === 0){
            clearInterval(interval);
            setIsActive(false);
            if(onComplete) onComplete();
        }
        return () => clearInterval(interval);
    }, [isActive, timeLeft, onComplete]);
    return {timeLeft, start: () => setIsActive(true), pause: () => setIsActive(false), reset: (s) => setTimeLeft(s)};
};
