import React, {useState} from "react";
import {authService} from '../services/api';
import NeumorphicCard from "./NeumorphicCard";

const AuthView = ({onAuthSuccess}) => {
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = async(e) => {
        e.preventDefault();
        setError('');
        try{
            if(isLogin) {
                const {data} = await authService.login(email, password);
                localStorage.setItem('token', data.access_token);
                onAuthSuccess(data.user);
            } else {
                await authService.signup(email, password);
                setIsLogin(true); //switching to login after successful signup
                alert("Account Created! Please Log In");
            }
        } catch (err){
            setError(err.response?.data?.detail || "Authentic failed");
        }
    };

    return (
        <NeumorphicCard title={isLogin ? "CHRONOS AUTH" : "CHRONOS SIGNUP"} className="auth-card">
            <h2 className = "text-3xl font-bold mb-8 text-center text-sky-400">
                {isLogin ? 'WELCOME BACK' : "CREATE ACCOUNT"}
            </h2>

            <form onSubmit={handleSubmit} className="space-y-6">
                <div className="space-y-2">
                    <label className="text-xs text-slate-400 ml-2">EMAIL ADDRESS</label>
                    <input 
                        type="email"
                        className="neumorphic-inset w-full p-4 text-white outline-none border-none"
                        value={email}
                        onChange = {(e) => setEmail(e.target.value)}
                        required />
                </div>
                <div className="space-y-2">
                    <label className="text-xs text-slate-400 ml-2">PASSWORD</label>
                    <input
                        type="password"
                        className="neumorphic-inset w-full p-4 text-white outline-none border-none"
                        value = {password}
                        onChange = {(e) => setPassword(e.target.value)}
                        required
                    />
                </div>

                {error && <p className = "text-red-500 text-sm text-center">{error}</p>}

                <button type="submit" className="w-full py-4 rounded-2xl bg-sky-500 text-slate-900 font-bold hover:bh-sky-400 transiition-colors
                shadow-lg shadow-sky-500/20">{isLogin ? 'LOG IN' : 'SIGN UP'}</button>
            </form>

            <button onClick={() => setIsLogin(!isLogin)}
            className = "w-full mt-6 text-sm text-slate-400 hover:text-sky-300 transition-colors">
                {isLogin ? "Don't have an account? Sign Up":"Already have an account? Login"}
            </button>
        </NeumorphicCard>
    );
};

export default AuthView;
