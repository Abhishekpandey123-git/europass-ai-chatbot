let sessionId = null;
const chatBox = document.getElementById('chatBox');
const chatForm = document.getElementById('chatForm');
const textInput = document.getElementById('textInput');
const fileInput = document.getElementById('fileInput');
const sendBtn = document.getElementById('sendBtn');
const filePreview = document.getElementById('filePreview');
const fileNameDisplay = document.getElementById('fileName');
const removeFileBtn = document.getElementById('removeFileBtn');
const pdfContainer = document.getElementById('pdfContainer');
const downloadPdfBtn = document.getElementById('downloadPdfBtn');

window.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch("/api/chat/start");
        const data = await response.json();
        sessionId = data.session_id;
        addMessage(data.bot_message, 'bot', true);
    } catch (error) {
        addMessage("Error connecting to the server. Please refresh.", 'bot', false);
    }
});

fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
        fileNameDisplay.innerText = fileInput.files[0].name;
        filePreview.classList.remove('hidden');
    }
});

removeFileBtn.addEventListener('click', () => {
    fileInput.value = "";
    filePreview.classList.add('hidden');
});

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = textInput.value.trim();
    const file = fileInput.files[0];
    if (!text && !file) return;

    let userMsg = text;
    if (file) userMsg = userMsg ? `[Attached: ${file.name}] ${userMsg}` : `[Attached Document: ${file.name}]`;
    addMessage(userMsg, 'user', false);

    await sendToServer(text, file);
});

async function sendToServer(text, file) {
    setLoading(true);
    const formData = new FormData();
    formData.append("session_id", sessionId);
    if (text) formData.append("text_message", text);
    if (file) formData.append("file", file);

    try {
        const response = await fetch("/api/chat/message", {
            method: "POST",
            body: formData
        });

        if (!response.ok) throw new Error("Failed to communicate with AI.");
        
        const data = await response.json();
        
        const allowSkip = data.state !== "READY_FOR_PDF" && data.state !== "AWAITING_ABOUT" && data.state !== "AWAITING_SKILLS";
        
        addMessage(data.bot_message, 'bot', allowSkip, data.state);

        if (data.state === "READY_FOR_PDF") {
            pdfContainer.classList.remove('hidden');
        }
    } catch (error) {
        addMessage("Sorry, an error occurred. Please try again.", 'bot', false);
    } finally {
        setLoading(false);
    }
}

downloadPdfBtn.addEventListener('click', async () => {
    try {
        downloadPdfBtn.innerText = "Generating...";
        downloadPdfBtn.disabled = true;

        const response = await fetch(`/api/generate-pdf/${sessionId}`);
        if (!response.ok) throw new Error("Failed to generate PDF.");

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = "Europass_CV.pdf";
        document.body.appendChild(a);
        a.click();
        a.remove();
    } catch (error) {
        alert(error.message);
    } finally {
        downloadPdfBtn.innerText = "Download Final Europass PDF";
        downloadPdfBtn.disabled = false;
    }
});

function addMessage(text, sender, showSkipButton = false, currentState = null) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', sender === 'user' ? 'user-msg' : 'bot-msg');
    
    const textSpan = document.createElement('span');
    textSpan.innerText = text;
    msgDiv.appendChild(textSpan);

    // Render "Skip Step" button if applicable
    if (sender === 'bot' && showSkipButton) {
        const skipBtn = document.createElement('button');
        skipBtn.innerText = "Skip Step";
        skipBtn.style.cssText = "display: block; margin-top: 8px; background: #e0e0e0; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.8em; font-weight: bold; color: #333;";
        skipBtn.onclick = async () => {
            skipBtn.remove();
            addMessage("Skip", 'user', false);
            await sendToServer("skip", null);
        };
        msgDiv.appendChild(skipBtn);
    }

    // Render "Write with AI" button styled simply like the Skip button
    const lowerText = text.toLowerCase();
    const isAboutPrompt = currentState === 'AWAITING_ABOUT' || lowerText.includes("about") || lowerText.includes("summary");
    
    if (sender === 'bot' && isAboutPrompt) {
        const aiBtn = document.createElement('button');
        aiBtn.innerText = "Write with AI";
        aiBtn.style.cssText = "display: block; margin-top: 8px; background: #e0e0e0; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.8em; font-weight: bold; color: #333;";
        aiBtn.onclick = async () => {
            aiBtn.remove();
            addMessage("Write with AI", 'user', false);
            await sendToServer("write", null);
        };
        msgDiv.appendChild(aiBtn);
    }

    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

let typingIndicator = null;
function setLoading(isLoading) {
    textInput.disabled = isLoading;
    sendBtn.disabled = isLoading;
    fileInput.disabled = isLoading;

    if (isLoading) {
        textInput.value = "";
        fileInput.value = "";
        filePreview.classList.add('hidden');
        
        typingIndicator = document.createElement('div');
        typingIndicator.classList.add('typing-indicator');
        typingIndicator.innerText = "Bot is typing (and reading documents)...";
        chatBox.appendChild(typingIndicator);
        chatBox.scrollTop = chatBox.scrollHeight;
    } else {
        if (typingIndicator) {
            typingIndicator.remove();
            typingIndicator = null;
        }
        textInput.focus();
    }
}