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

// Initialize the chat on load
window.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch("http://127.0.0.1:8000/api/chat/start");
        const data = await response.json();
        sessionId = data.session_id;
        addMessage(data.bot_message, 'bot');
    } catch (error) {
        addMessage("Error connecting to the server. Please refresh.", 'bot');
    }
});

// Display file preview when a file is selected
fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
        fileNameDisplay.innerText = fileInput.files[0].name;
        filePreview.classList.remove('hidden');
    }
});

// Remove file from staging
removeFileBtn.addEventListener('click', () => {
    fileInput.value = "";
    filePreview.classList.add('hidden');
});

// Handle form submission
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const text = textInput.value.trim();
    const file = fileInput.files[0];
    
    if (!text && !file) return;

    // Display user message
    let userMsg = text;
    if (file) userMsg = userMsg ? `[Attached: ${file.name}] ${userMsg}` : `[Attached Document: ${file.name}]`;
    addMessage(userMsg, 'user');

    // Lock UI and prepare request
    setLoading(true);
    const formData = new FormData();
    formData.append("session_id", sessionId);
    if (text) formData.append("text_message", text);
    if (file) formData.append("file", file);

    try {
        const response = await fetch("http://127.0.0.1:8000/api/chat/message", {
            method: "POST",
            body: formData
        });

        if (!response.ok) throw new Error("Failed to communicate with AI.");
        
        const data = await response.json();
        addMessage(data.bot_message, 'bot');

        // If the AI says we are ready, show the download button
        if (data.state === "READY_FOR_PDF") {
            pdfContainer.classList.remove('hidden');
        }

    } catch (error) {
        addMessage("Sorry, an error occurred. Please try again.", 'bot');
    } finally {
        setLoading(false);
    }
});

// Handle PDF Download
downloadPdfBtn.addEventListener('click', async () => {
    try {
        downloadPdfBtn.innerText = "Generating...";
        downloadPdfBtn.disabled = true;

        const response = await fetch(`http://127.0.0.1:8000/api/generate-pdf/${sessionId}`);
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

// Utility: Add message to chat box
function addMessage(text, sender) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', sender === 'user' ? 'user-msg' : 'bot-msg');
    msgDiv.innerText = text;
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// Utility: Lock/Unlock UI
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