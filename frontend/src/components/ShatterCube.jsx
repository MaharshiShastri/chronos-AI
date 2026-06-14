import React, {useEffect, useState} from 'react';
import '../styles.css';


const ShatterCube = ({isShattered, onComplete}) => {
    const [shattered, setShattered] = useState(false);
    useEffect(() => {
    
        const shatterTimer = setTimeout(() => {
        setShattered(true);
    }, 500); // Match this to your CSS animation duration
    
    const completeTimer = setTimeout(() => {

        if(onComplete) onComplete();
    }, 1500); // Ensure this is after the animation completes
    return () =>{
        clearTimeout(shatterTimer);
        clearTimeout(completeTimer);
    };
}, [onComplete]);

    return (
        <div className={`scene ${isShattered ? 'shattered' : ''}`}>
            <div className="cube">
                <div className="face front">CHRONOS</div>
                <div className="face back">AI</div>
                <div className="face right">FOCUS</div>
                <div className="face left">TASK</div>
                <div className='face top'>TIME</div>
                <div className='face bottom'>DONE</div>
            </div>
        </div>
    );
};

export default ShatterCube;