let isLoginMode = true;
let abortControl = null;
let conversationID = null;
const localHost = "http://localhost:8000"



function setAuthMode(login){

    isLoginMode = login;

    const switchBg = document.getElementById("switch-bg");
    const labels = document.querySelectorAll(".switch-label");
    const title = document.getElementById("auth-title");
    const btn = document.getElementById("auth-btn");
    const link = document.getElementById("toggle-link");
    if(isLoginMode){
        switchBg.style.left = "4px";
        title.innerText = "IDENTITY VERIFICATION";
        btn.innerText = "AUTHENTICATE";
        link.innerText = "EXISTING USER AUTHORIZATION";
        labels[0].classList.add("activate-label");
        labels[1].classList.remove("activate-label");
    } else {
        switchBg.style.left = "calc(50% - 4px)";
        title.innerText = "INITITALIZE ID";
        btn.innerText = "REGISTER ENTITY";
        link.innerText = "NEW NODE DETECTION";
        labels[1].classList.add("activate-label");
        labels[0].classList.remove("activate-label");
    }

}

window.onload = () => setAuthMode(true);

//Authentication flow
async function handleAuth(){
    const email = document.getElementById("auth-email").value;
    const password = document.getElementById("auth-pass").value;
    const endPoint = isLoginMode ? "/login" : "/signup";
    if(!email || !password){
        alert("REQUIRED DATA MISSING\n" + `${email} or ${password} is missing.`);
        return;
    }
    try{
        const response = await fetch(`${localHost}${endPoint}`, {
            method: "POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify({email, password})
        });
        const contentType = response.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
            const text = await response.text();
            console.error("Received non-JSON response:", text);
            throw new Error("Server returned HTML instead of JSON. Check your URL/Port.");
        }
        const data = await response.json();
        if(response.ok){
            if(isLoginMode){
                localStorage.setItem("token", data.access_token);
                localStorage.setItem("user", JSON.stringify(data.user));
                showChatInterface();
            } else {
                alert(`REGISTRATION COMPLETE FOR EMAIL: ${response.email}. PROCEEDING TO AUTHENTICATION.`);
                setAuthMode(true);
            }
        } else {
            alert(`ACCESS_DENIED: "Invalid Credentials"`);
            console.log(`${data.detail}`)
        }
    } catch (err){
        console.error("Link Failure: ", err);
    }
}

async function fetchChatHistory(){
    const token = localStorage.getItem("token");
    const messageContainer = document.getElementById("messages");
    try{
        const conversation_ID = JSON.parse(localStorage.getItem("user"));
        if(conversation_ID){
            const response = await fetch(`${localHost}/conversation/${conversation_ID.id}`, {
                headers: {"Authorization": `Bearer ${token}`}
            });
            if(response.ok){
                const history = await response.json();
                messageContainer.innerHTML = "";
                const recentMessages = history.slice(-6);
                recentMessages.forEach(msg => {
                    appendMessage(msg.content, msg.role.toLowerCase() === "user" ? "User" : "AI");
                });
            } else {
                alert(`ERROR DETECTED: ${response}`);
            }
        } else {
            alert("Unable to load localStorage");
        }
    } catch(err){
        console.error("HISTORY LOAD FAIL: ", err);
        appendMessage("HISTORY_OFFLINE: Starting new session.", "ai");
    }

}

async function showChatInterface(){
    const authContent = document.getElementById("auth-content");
    const headerZone = document.querySelector(".header-zone");
    const authPage = document.getElementById("auth-page");
    const chatPage = document.getElementById("chat-page");
    const userDisplay = document.getElementById("user-display");
    const activeNode = document.querySelector(".active-node");
    const loaderModal = document.getElementById("loader-modal");
    const labels = document.querySelectorAll(".switch-label");

    if(authPage && chatPage){
        authContent.classList.add("hidden");
        loaderModal.classList.remove("hidden");
        loaderModal.style.display = "flex";
        headerZone.classList.add("loading");
        labels.forEach(l => l.classList.add("success"));
        
        document.querySelector(".status-dot").style.background = "#10b981";
        document.querySelector(".status-dot").style.boxShadow = "0 0 15px #10b981";
        let history = []
        try{
            const historyData = await fetchChatHistory();
            history = Array.isArray(historyData) ? historyData : [];
        } catch (err){
            console.warn("History failed to be fetched, starting with empty cube");
            history = [];
        }
        
        console.log(history);
        const faces = document.querySelectorAll(".face");
        const snippets = history.slice(-6);
        faces.forEach((face, i) => {
            if(snippets[i]){
                face.innerText = snippets[i].content.substring(0, 20) + "...";
            } else {
                face.innerText = `DATA POINT 0${i+1}`;
            }
        });

        const statusText = document.getElementById('loader-status');
        
        statusText.innerText = "FETCHING_HISTORY...";
        statusText.style.color = "#38bdf8"; // Blue
        await new Promise(r => setTimeout(r, 5000));

        statusText.innerText = "DECRYPTING_PACKETS...";
        statusText.style.color = "#10b981"; // Green
        await new Promise(r => setTimeout(r, 5000));

        statusText.innerText="CRITICAL MASS REACHED";
        statusText.style.color = "#f43f5e";

        const cube = document.querySelector(".cube");
        
        cube.classList.add("spinning-fast");
        await new Promise(r => setTimeout(r, 2000));

        statusText.innerText = "CHATBOX EXPANSION COMPLETE";
        cube.classList.remove("spinning-fast");
        cube.classList.add("shattered");
        await new Promise(r => setTimeout(r, 800));


        authPage.style.display = "none";
        loaderModal.classList.add("hidden");
        chatPage.style.display = "flex";
        chatPage.style.alignItems = "stretch";
        chatPage.style.background = "#020617";
        setTimeout (() => {
            chatPage.style.transition = "opacity 1s";
            chatPage.style.opacity = "1";
        }, 10);
        
        loadSidebarSessions();

        const userInfo = JSON.parse(localStorage.getItem("user"));
        if(userInfo){
        activeNode.innerText = `NODE ${userInfo.id}`;
        userDisplay.innerText = `// ${userInfo.email.toUpperCase()}`;
        }
        console.log("System Transition: UI_CHAT_ENABLED");
    }else {
        console.error("UI Error: Target elements not found in DOM.");
    }
}

function handleLogout(){
    localStorage.removeItem("token");
    conversationID = null;

    console.log("System reset: IDENTITY DEPROVISIONED");
    window.location.reload();
}

async function fetChatHistory() {
    const token = localStorage.getItem("token");
    const container = document.getElementById("messages");
    try{
        const user = JSON.parse(localStorage.getItem("user"));
        const response = await fetch(`${localHost}/conversation/${user.id}`, {
            headers: {"Authorization":`Bearer ${token}`}
        });

        const history = await response.json();
        container.innerHTML = "";

        history.slice(-6).forEach(msg => appendMessage(msg.content, msg.role === "user"? "user": "ai"));
        return history;
    } catch(e) {return [];}
}

//Optimized streaming logic
async function sendMessage(){

    const input = document.getElementById("input");
    const text = input.value.trim();
    if(!text) return;

    abortControl = new AbortController();
    document.getElementById("stop-btn").classList.remove("hidden");

    appendMessage(text, "user");
    input.value = "";

    const aiBox = appendMessage("Thinking...", "ai");
    aiBox.innerText = "";
    
    const token = localStorage.getItem("token");

    try{
        const response = await fetch(`${localHost}/chat-stream`,{
            method: "POST",
            headers: {
                "Content-Type" : "application/json",
                "Authorization" : `Bearer ${token}`
            },
            body:JSON.stringify({ message: text, conversation_id: conversationID})
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while(true){
            const {done, value} = await reader.read();
            if(done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split("\n");
            for(const line of lines){
                if(line.startsWith("data: ")){
                    const data = JSON.parse(line.replace("data: ", ""));
                    if(data.token) aiBox.innerText += data.token;
                    if(data.conversation_id) conversationID = data.conversation_id;
                    scrollToBottom();
                }
            }
        }
    } catch(err){
        if (err.name === 'AbortError') aiBox.innerText += " [STREAM ABORTED]";
        else aiBox.innerText = "CRITICAL ERROR: DATA STREAM CORRUPTED";
    } finally {
        document.getElementById("stop-btn").classList.add("hidden");
    }
}

function stopGeneration(){
    if(abortControl){
        abortControl.abort();
        console.log("Stream Terminated by user");
    }
}

function loadSidebarSessions(){
    const list = document.getElementById('chat-history-list');
    list.innerHTML = `<div class="history-item" onclick="location.reload()">Current Session</div>`;
}

function appendMessage(text, role){

    const msg = document.createElement("div");

    msg.className = `message ${role.toLowerCase()}`;
    msg.innerText = text;
    
    document.getElementById("messages").appendChild(msg);
    scrollToBottom();
    return msg;
}

function scrollToBottom(){
    const m = document.getElementById("messages");
    m.scrollTop = m.scrollHeight;
}



window.addEventListener('DOMContentLoaded', () => {

    const savedToken = localStorage.getItem("token");
    if(savedToken){
        console.log("Session Recovery: TOKEN_VALIDATE");
        showChatInterface();
    }
});