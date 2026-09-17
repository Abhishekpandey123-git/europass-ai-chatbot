let sessionId = null;
let preferredMode = "doc"; // "doc" or "manual"
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
const cvPreviewContent = document.getElementById('cvPreviewContent');

const entryModal = document.getElementById('entryModal');
const modalNewSession = document.getElementById('modalNewSession');
const modalRestoreSlip = document.getElementById('modalRestoreSlip');
const modalEnterToken = document.getElementById('modalEnterToken');
const tokenInput = document.getElementById('tokenInput');
const slipFileInput = document.getElementById('slipFileInput');

setupSlipControls();

if (modalNewSession) {
    modalNewSession.onclick = async () => {
        try {
            const response = await fetch("/api/chat/start");
            const data = await response.json();
            sessionId = data.session_id;
            
            if (entryModal) {
                entryModal.style.display = 'none';
                entryModal.classList.add('hidden');
            }
            if (data.cv) updateLivePreview(data.cv);
            showModeSelectionPrompt(data);
        } catch (error) {
            alert("Error starting new session.");
        }
    };
}

if (modalRestoreSlip) {
    modalRestoreSlip.onclick = () => {
        if (slipFileInput) slipFileInput.click();
    };
}

if (slipFileInput) {
    slipFileInput.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append("file", file);

        try {
            const response = await fetch("/api/session/restore-slip", {
                method: "POST",
                body: formData
            });
            if (!response.ok) throw new Error("Failed to restore session slip.");
            
            const data = await response.json();
            sessionId = data.session_id;
            chatBox.innerHTML = "";
            
            if (data.chat_history && Array.isArray(data.chat_history) && data.chat_history.length > 0) {
                data.chat_history.forEach(msg => {
                    addMessage(msg.text, msg.sender, false, msg.state);
                });
            } else {
                addMessage(data.bot_message, 'bot', false, data.state);
            }

            pdfContainer.classList.remove('hidden');
            if (data.cv) updateLivePreview(data.cv);
            if (entryModal) {
                entryModal.style.display = 'none';
                entryModal.classList.add('hidden');
            }
        } catch (err) {
            alert("Error restoring slip: " + err.message);
        }
    };
}

if (modalEnterToken) {
    modalEnterToken.onclick = async () => {
        const token = tokenInput.value.trim();
        if (!token) {
            alert("Please enter a valid session token.");
            return;
        }
        sessionId = token;
        if (entryModal) {
            entryModal.style.display = 'none';
            entryModal.classList.add('hidden');
        }
        
        try {
            const formData = new FormData();
            formData.append("session_id", sessionId);
            formData.append("text_message", "resume");
            
            const response = await fetch("/api/chat/message", { method: "POST", body: formData });
            if (!response.ok) throw new Error("Session invalid or expired.");
            const data = await response.json();
            if (data.cv) updateLivePreview(data.cv);
            
            chatBox.innerHTML = "";
            if (data.chat_history && Array.isArray(data.chat_history) && data.chat_history.length > 0) {
                data.chat_history.forEach(msg => {
                    addMessage(msg.text, msg.sender, false, msg.state);
                });
            } else {
                addMessage("Session token accepted! Resuming your workflow...", 'bot', false, data.state);
                addMessage(data.bot_message, 'bot', true, data.state);
            }
            pdfContainer.classList.remove('hidden');
        } catch (err) {
            alert("Could not resume session with that token. Starting a fresh session.");
            const response = await fetch("/api/chat/start");
            const data = await response.json();
            sessionId = data.session_id;
            if (data.cv) updateLivePreview(data.cv);
            addMessage(data.bot_message, 'bot', true, data.state);
        }
    };
}

function showModeSelectionPrompt(data) {
    addMessage("Welcome! Please choose your preferred input style to proceed:", 'bot', false);
    
    const modeDiv = document.createElement('div');
    modeDiv.style.cssText = "display: flex; gap: 10px; margin-top: 10px; position: relative; z-index: 10;";
    
    const docBtn = document.createElement('button');
    docBtn.innerText = "Document Upload Mode";
    docBtn.style.cssText = "background: #3182ce; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 0.85em; font-weight: bold; pointer-events: auto;";
    docBtn.onclick = () => {
        preferredMode = "doc";
        modeDiv.remove();
        addMessage("Selected: Document Upload Mode", 'user', false);
        addMessage(data.bot_message, 'bot', true, data.state);
    };

    const manualBtn = document.createElement('button');
    manualBtn.innerText = "Manual Typing Mode";
    manualBtn.style.cssText = "background: #38a169; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 0.85em; font-weight: bold; pointer-events: auto;";
    manualBtn.onclick = () => {
        preferredMode = "manual";
        modeDiv.remove();
        addMessage("Selected: Manual Typing Mode", 'user', false);
        addMessage("Great! You can type your information directly into the chat box at any step. Let's start with your profile photo (or type Skip):", 'bot', true, data.state);
    };

    modeDiv.appendChild(docBtn);
    modeDiv.appendChild(manualBtn);
    chatBox.appendChild(modeDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// Clean Dynamic Europass Renderer using stylesheet-driven backgrounds
function updateLivePreview(cv) {
    if (!cvPreviewContent) return;

    if (!cv || (!cv.personal_info?.first_name && !cv.about_me && cv.work_experience.length === 0 && cv.education.length === 0 && !cv.profile_image_base64)) {
        cvPreviewContent.innerHTML = '<p class="placeholder-text" style="color: #888;">Your live CV summary will appear here once data extraction begins...</p>';
        return;
    }

    const p = cv.personal_info || {};
    const fullName = `${p.first_name || ''} ${p.last_name || ''}`.trim();

    let html = `
    <div class="euro-page page-1">
        <div style="position: relative; z-index: 2; padding: 35mm 20mm 25mm 20mm; font-family: Arial, sans-serif; color: #333333; font-size: 12px; line-height: 1.5;">
            <div style="display: flex; gap: 15px; margin-top: 15px; margin-bottom: 20px; align-items: flex-start;">
    `;

    if (cv.profile_image_base64) {
        html += `
                <div style="flex-shrink: 0;">
                    <img src="data:image/jpeg;base64,${cv.profile_image_base64}" style="width: 80px; height: 100px; object-fit: cover; border-radius: 4px; border: 1px solid #cbd5e0;" />
                </div>
        `;
    }

    html += `
                <div style="flex-grow: 1;">
                    <h1 style="color: #5b358c; font-size: 18px; margin: 0 0 6px 0; text-transform: uppercase;">${fullName || 'Full Name'}</h1>
                    ${p.phone ? `<div style="margin-bottom: 2px; color: #4a5568;"><b>Phone number:</b> ${p.phone}</div>` : ''}
                    ${p.email ? `<div style="margin-bottom: 2px; color: #4a5568;"><b>Email address:</b> ${p.email}</div>` : ''}
                    ${p.address ? `<div style="margin-bottom: 2px; color: #4a5568;"><b>Home:</b> ${typeof p.address === 'object' ? `${p.address.line1 || ''} ${p.address.city || ''} ${p.address.country || ''}` : p.address}</div>` : ''}
                </div>
            </div>
    `;

    if (cv.about_me) {
        html += `
            <div style="margin-bottom: 20px;">
                <h2 style="font-size: 13px; color: #5b358c; border-bottom: 1.5px solid #5b358c; padding-bottom: 2px; margin: 0 0 8px 0; letter-spacing: 0.5px;">ABOUT ME</h2>
                <p style="margin: 0; color: #4a5568; text-align: justify;">${cv.about_me}</p>
            </div>
        `;
    }

    if (cv.education && cv.education.length > 0) {
        html += `
            <div style="margin-bottom: 20px;">
                <h2 style="font-size: 13px; color: #5b358c; border-bottom: 1.5px solid #5b358c; padding-bottom: 2px; margin: 0 0 8px 0; letter-spacing: 0.5px;">EDUCATION AND TRAINING</h2>
        `;
        cv.education.forEach(edu => {
            html += `
                <div style="margin-bottom: 10px;">
                    <div style="font-weight: bold; color: #2d3748;">${edu.title || ''}</div>
                    <div style="display: flex; justify-content: space-between; color: #4a5568; font-weight: bold;">
                        <span>${edu.organization || ''}</span>
                        <span style="color: #718096; font-weight: normal;">[${edu.start_date || ''} – ${edu.end_date || 'Present'}]</span>
                    </div>
                </div>
            `;
        });
        html += `</div>`;
    }

    html += `</div></div>`;

    const workItems = cv.work_experience || [];
    const hasSkills = cv.digital_skills && cv.digital_skills.length > 0;

    if (workItems.length > 0 || hasSkills) {
        html += `
        <div class="euro-page page-2">
            <div style="position: relative; z-index: 2; padding: 35mm 20mm 25mm 20mm; font-family: Arial, sans-serif; color: #333333; font-size: 12px; line-height: 1.5;">
        `;

        if (workItems.length > 0) {
            html += `
                <div style="margin-bottom: 20px; margin-top: 15px;">
                    <h2 style="font-size: 13px; color: #5b358c; border-bottom: 1.5px solid #5b358c; padding-bottom: 2px; margin: 0 0 8px 0; letter-spacing: 0.5px;">WORK EXPERIENCE</h2>
            `;
            workItems.forEach(work => {
                html += `
                    <div style="margin-bottom: 10px;">
                        <div style="color: #4a5568; font-weight: bold;">${work.employer || ''}</div>
                        <div style="font-weight: bold; color: #2d3748; display: flex; justify-content: space-between;">
                            <span>${work.title || ''}</span>
                            <span style="color: #718096; font-weight: normal;">${work.start_date || ''} – ${work.end_date || 'Present'}</span>
                        </div>
                        ${work.description ? `<p style="margin: 4px 0 0 0; color: #4a5568;">${work.description}</p>` : ''}
                    </div>
                `;
            });
            html += `</div>`;
        }

        if (hasSkills) {
            html += `
                <div style="margin-bottom: 20px;">
                    <h2 style="font-size: 13px; color: #5b358c; border-bottom: 1.5px solid #5b358c; padding-bottom: 2px; margin: 0 0 8px 0; letter-spacing: 0.5px;">SKILLS</h2>
                    <div style="font-weight: bold; color: #2d3748; margin-bottom: 2px;">Digital Skills</div>
                    <div style="color: #4a5568;">${cv.digital_skills.join(' / ')}</div>
                </div>
            `;
        }

        html += `</div></div>`;
    }

    cvPreviewContent.innerHTML = html;
}

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

        if (response.status === 401) {
            alert("Your 24-hour session window has expired! Please upload your saved 'europass_slip.json' file or enter your token to resume.");
            setLoading(false);
            if (entryModal) {
                entryModal.style.display = 'flex';
                entryModal.classList.remove('hidden');
            }
            return;
        }

        if (!response.ok) throw new Error("Failed to communicate with AI.");
        
        const data = await response.json();
        
        if (data.cv) {
            updateLivePreview(data.cv);
        }
        
        const allowSkip = data.state !== "READY_FOR_PDF" && 
                          data.state !== "PREVIEW_READY" && 
                          data.state !== "AWAITING_REVISION" && 
                          data.state !== "AWAITING_ABOUT" && 
                          data.state !== "AWAITING_SKILLS" &&
                          data.state !== "AWAITING_MANUAL_PURPOSE" &&
                          data.state !== "AWAITING_MANUAL_CONTACT" &&
                          data.state !== "AWAITING_MANUAL_SKILLS_HOBBIES";
        
        addMessage(data.bot_message, 'bot', allowSkip, data.state);

        if (data.state === "READY_FOR_PDF" || data.state === "PREVIEW_READY" || data.state === "AWAITING_REVISION") {
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

    if (sender === 'bot' && showSkipButton) {
        const skipBtn = document.createElement('button');
        skipBtn.innerText = "Skip Step";
        skipBtn.style.cssText = "display: block; margin-top: 8px; background: #e0e0e0; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.8em; font-weight: bold; color: #333; pointer-events: auto;";
        skipBtn.onclick = async () => {
            skipBtn.remove();
            addMessage("Skip", 'user', false);
            await sendToServer("skip", null);
        };
        msgDiv.appendChild(skipBtn);
    }

    const isAboutPrompt = currentState === 'AWAITING_ABOUT';
    if (sender === 'bot' && isAboutPrompt) {
        const aiBtn = document.createElement('button');
        aiBtn.innerText = "Write with AI";
        aiBtn.style.cssText = "display: block; margin-top: 8px; background: #e0e0e0; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.8em; font-weight: bold; color: #333; pointer-events: auto;";
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
        typingIndicator.innerText = "Bot is typing (and processing data)...";
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

function setupSlipControls() {
    const controlsDiv = document.createElement('div');
    controlsDiv.style.cssText = "padding: 10px; background: #f4f6f8; display: flex; gap: 10px; align-items: center; justify-content: center; border-bottom: 1px solid #ddd;";
    
    const downloadSlipBtn = document.createElement('button');
    downloadSlipBtn.innerText = "Download Session Slip";
    downloadSlipBtn.style.cssText = "background: #2b6cb0; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 0.85em; font-weight: bold; pointer-events: auto;";
    downloadSlipBtn.onclick = async () => {
        if (!sessionId) {
            alert("No active session found.");
            return;
        }
        window.location.href = `/api/session/download-slip/${sessionId}`;
    };

    controlsDiv.appendChild(downloadSlipBtn);
    const chatContainer = document.querySelector('.chat-container') || chatBox.parentElement;
    chatContainer.insertBefore(controlsDiv, chatBox);
}

// Client-side PDF Download for Live Preview with Clean Background Processing
function downloadLivePreviewPDF() {
    const element = document.getElementById('cvPreviewContent');
    if (!element || element.innerText.includes("Your live CV summary will appear here")) {
        alert("No CV content available to download yet!");
        return;
    }

    const options = {
        margin:       0,
        filename:     'Europass_CV_Preview.pdf',
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { 
            scale: 2, 
            useCORS: true, 
            letterRendering: true,
            backgroundColor: null 
        },
        jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' },
        pagebreak:    { mode: ['css', 'legacy'] }
    };

    html2pdf().from(element).set(options).save();
}