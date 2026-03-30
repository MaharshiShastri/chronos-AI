import axios from 'axios';
const API_URL = "http://127.0.0.1:8000"
const API = axios.create({
    baseURL : API_URL,
});

API.interceptors.request.use((config) => {
    const token = localStorage.getItem("token");
    if(token)  config.headers.Authorization = `Bearer ${token}`;
    return config;
});

const fetchStream = async(endpoint, body, onChunk) => {
    const token = localStorage.getItem('token');
    const response = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(body)
    });

    if (response.status === 401) throw new Error("UNAUTHORIZED");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while(true){
        const {done, value} = await reader.read();
        if(done) break;
        buffer += decoder.decode(value, {stream: true});
        const lines = buffer.split("\n");
        buffer = lines.pop();
        for(const line of lines){
            if(line.startsWith("data: ")){
                try{
                    const jsonString = line.replace("data: ", "");
                    const data = JSON.parse(jsonString);

                    if(data.token)  onChunk(data.token);
                    if(data.conversation_id)    localStorage.setItem("current_conv_id", data.conversation_id);
                } catch(e) {
                    console.error("Error parsing SSE line:", e);
                }
            }
        }
    }
}
export const authService = {
    login: (email, password) => API.post("/login", {email, password}),
    signup: (email, password) => API.post("/signup", {email, password}),
};

export const aiService = {
    // Stream plans
    streamPlan: (task, time_budget, conversationid, mode,  onChunk) => {
        const id = conversationid ? parseInt(conversationid) : null;
        return fetchStream("/plan", { task, time_budget, mode: mode, conversation_id: id }, onChunk);
    },
    //Stream chat
    streamChat: (history, conversationid, onChunk) => {
        const id = conversationid ? parseInt(conversationid) : null;
        return fetchStream("/chat-stream", { message: history, conversation_id: id }, onChunk);
    },
    //Get chat history
    getChatHistory: (conversationid) => {
        const id = conversationid ? parseInt(conversationid) : null;
        return API.get(`/conversation/${id}`);
    },
    //Get conversations
    getConversations: () => API.get("/conversations"),
    //Get previous tasks
    getTasks: () => API.get("/tasks"),
    //Delete conversation
    deleteConversation: (conversationID) => API.delete(`/conversation/${conversationID}`),
    //Rrename conversation
    renameConversation: (conversationID, newName) => API.put(`/conversation/${conversationID}`, {title: newName}),
};
