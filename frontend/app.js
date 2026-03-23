let conversationID = null;
let isLoading = false;

function addMessage(text, role){
    const msg = document.createElement("div");
    msg.className = `messaage ${role}`;
    msg.innerText = text;
    
    document.getElementById("messages").appendChild(msg);
    scrollToBottom();  
    
    return msg;
}

function scrollToBottom(){
    const container = document.getElementById("messages");
    container.scrollTop = container.scrollHeight;
}

async function typeText(element, text){
    element.innerText = "";

    for(let i = 0; i < text.length; i++){
        element.innerText += text.slice(0, i+1) + "▌";
        await new Promise(res => setTimeout(res, 8));
    }
}

async function sendMessage(){
    if(isLoading) return;

    const input = document.getElementById("input");
    const button = document.querySelector("button");

    const text = input.value.trim();
    if(!text) return;

    isLoading = true;
    button.disabled = true;

    addMessage(text, "user");
    input.value = "";

    const responseDiv = addMessage("Thinking...", "ai");
    setTimeout(() => {responseDiv.innerText = "";}, 300);
    console.log("Sending request...");
    try{
        const response = await fetch("http://127.0.0.1:8000/chat-stream", {
            method: "POST",
            headers: {
                "Content-Type" : "application/json"
            },
            body: JSON.stringify({
                message: text,
                conversation_id: conversationID
            })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");

        let fullText = "";
        let queue = [];
        let isTyping = false;        

        async function processQueue(){
            if(isTyping) return;
            
            while(queue.length > 0){
                const char = queue.shift();
                responseDiv.innerText += char;
                scrollToBottom();

                await new Promise(res => setTimeout(res, 8));
            }
            isTyping = false;
        }


        while(true){
            const {done, value} = await reader.read();
            if(done) break;

            const chunk = decoder.decode(value, {stream: true});
            fullText += chunk;

            for(let char of chunk){
                queue.push(char);
            }

            processQueue();
        }
    } catch (err) {
        responseDiv.innerText = "Error Getting Response";
        console.log(err);
    }
    isLoading = false;
    button.disabled = false;
}