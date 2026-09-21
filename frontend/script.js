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
const reviewButton = document.getElementById('reviewButton');
const downloadPreviewBtn = document.getElementById('downloadPreviewBtn');
const cvPreviewContent = document.getElementById('cvPreviewContent');
const editorBox = document.getElementById('editorBox');

let currentLoadedCV = null;

const entryModal = document.getElementById('entryModal');
const modalNewSession = document.getElementById('modalNewSession');
const modalRestoreSlip = document.getElementById('modalRestoreSlip');
const modalEnterToken = document.getElementById('modalEnterToken');
const tokenInput = document.getElementById('tokenInput');
const slipFileInput = document.getElementById('slipFileInput');

setupSlipControls();

if (reviewButton) {
    reviewButton.addEventListener('click', async () => {
        if (!sessionId) {
            alert("Please start a session first!");
            return;
        }
        addMessage("Review CV & Check Gaps", 'user', false);
        await sendToServer("review", null);
    });
}

if (downloadPreviewBtn) {
    downloadPreviewBtn.addEventListener('click', downloadLivePreviewPDF);
}

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

// Professional Europass Renderer matching Reference Layouts
function updateLivePreview(cv) {
    if (!cvPreviewContent) return;
    currentLoadedCV = cv;

    if (!cv || (!cv.personal_info?.first_name && !cv.about_me && cv.work_experience.length === 0 && cv.education.length === 0 && !cv.profile_image_base64)) {
        cvPreviewContent.innerHTML = '<p class="placeholder-text" style="color: #888;">Your live CV summary will appear here once data extraction begins...</p>';
        if (editorBox) {
            editorBox.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; min-height: 350px; padding: 30px; text-align: center; background: #ffffff; border: 2px dashed #cbd5e0; border-radius: 8px; margin: 4px;">
                    <div style="font-size: 36px; margin-bottom: 12px;">🗂️</div>
                    <h3 style="font-size: 15px; color: #1e293b; margin-bottom: 6px; font-weight: bold;">Section Editor Window</h3>
                    <p style="font-size: 12px; color: #64748b; line-height: 1.5; max-width: 240px;">Sections will populate here as an interactive window once a session begins.</p>
                </div>
            `;
        }
        return;
    }

    cvPreviewContent.innerHTML = renderTemplatePreview(cv);
    renderManualEditor(cv);
    return;

    const p = cv.personal_info || {};
    const fullName = `${p.first_name || ''} ${p.last_name || ''}`.trim();
    const nationalityStr = Array.isArray(p.nationality) ? p.nationality.join(', ') : (p.nationality || '');

    let html = `
    <div class="euro-page page-1">
        <div style="position: relative; z-index: 2; padding: 35mm 20mm 25mm 20mm; font-family: Arial, sans-serif; color: #333333; font-size: 12px; line-height: 1.5;">
            <div style="display: flex; gap: 20px; margin-top: 15px; margin-bottom: 20px; align-items: flex-start;">
    `;

    if (cv.profile_image_base64) {
        html += `
                <div style="flex-shrink: 0;">
                    <img src="data:image/jpeg;base64,${cv.profile_image_base64}" style="width: 90px; height: 110px; object-fit: cover; border-radius: 50%; border: 2px solid #cbd5e0;" />
                </div>
        `;
    }

    html += `
                <div style="flex-grow: 1;">
                    <h1 style="color: #5b358c; font-size: 18px; margin: 0 0 6px 0; text-transform: uppercase;">${fullName || 'Full Name'}</h1>
                    ${p.passport ? `<div style="margin-bottom: 2px; color: #4a5568;"><b>Passport:</b> ${p.passport}</div>` : ''}
                    ${nationalityStr ? `<div style="margin-bottom: 2px; color: #4a5568;"><b>Nationality:</b> ${nationalityStr}</div>` : ''}
                    ${p.date_of_birth ? `<div style="margin-bottom: 2px; color: #4a5568;"><b>Date of birth:</b> ${p.date_of_birth}</div>` : ''}
                    ${p.gender ? `<div style="margin-bottom: 2px; color: #4a5568;"><b>Gender:</b> ${p.gender}</div>` : ''}
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
                <p style="margin: 0; color: #4a5568; text-align: justify; line-height: 1.6;">${cv.about_me}</p>
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
    renderManualEditor(cv);
}

function escapePreviewText(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function previewAddress(address) {
    if (!address) return '';
    if (typeof address === 'string') return address;
    return [address.line1, address.city, address.postal_code, address.country]
        .filter(Boolean)
        .join(', ');
}

function renderPreviewSection(title, content) {
    if (!content) return '';
    return `<section class="cv-template-section"><h2>${title}</h2>${content}</section>`;
}

function renderTemplatePreview(cv) {
    const p = cv.personal_info || {};
    const fullName = `${p.first_name || ''} ${p.last_name || ''}`.trim() || 'FULL NAME';
    const address = previewAddress(p.address);
    const nationality = Array.isArray(p.nationality) ? p.nationality.join(', ') : (p.nationality || '');
    const education = (cv.education || []).map(item => `<article class="cv-entry"><h3>${escapePreviewText(item.title)}</h3><div class="cv-entry-meta"><strong>${escapePreviewText(item.organization)}</strong><span>${escapePreviewText(item.start_date)} - ${escapePreviewText(item.end_date || 'Ongoing')}</span></div><div class="cv-entry-location">${escapePreviewText([item.city, item.country].filter(Boolean).join(', '))}</div>${item.description ? `<p>${escapePreviewText(item.description)}</p>` : ''}</article>`).join('') || '<div class="preview-placeholder">DEGREE / QUALIFICATION<br>Institution Name [MM/YYYY - MM/YYYY]</div>';
    const work = (cv.work_experience || []).map(item => `<article class="cv-entry"><h3>${escapePreviewText(item.employer)}${item.city || item.country ? ` - ${escapePreviewText([item.city, item.country].filter(Boolean).join(', '))}` : ''}</h3><strong>${escapePreviewText(item.title)}</strong><div class="cv-entry-meta"><span>${escapePreviewText(item.start_date)} - ${escapePreviewText(item.end_date || 'CURRENT')}</span></div>${item.description ? `<p>${escapePreviewText(item.description)}</p>` : ''}</article>`).join('') || '<div class="preview-placeholder">COMPANY NAME - CITY, COUNTRY<br>JOB TITLE<br>[MM/YYYY - CURRENT]</div>';
    const languages = (cv.other_languages || []).map(item => `<div class="language-entry"><strong>${escapePreviewText(item.language)}</strong><span>LISTENING ${escapePreviewText(item.listening)} &nbsp; READING ${escapePreviewText(item.reading)} &nbsp; WRITING ${escapePreviewText(item.writing)}</span><span>SPOKEN PRODUCTION ${escapePreviewText(item.spoken_production)} &nbsp; SPOKEN INTERACTION ${escapePreviewText(item.spoken_interaction)}</span></div>`).join('') || '<div class="preview-placeholder">[LANGUAGE] - LISTENING [B2] - READING [B2] - WRITING [B2]</div>';
    const photo = cv.profile_image_base64 ? `<img class="cv-template-photo" src="data:image/jpeg;base64,${cv.profile_image_base64}" alt="Profile photo">` : '<div class="cv-template-photo preview-placeholder">PROFILE<br>PHOTO</div>';
    const section = (title, content) => `<section class="cv-template-section"><h2>${title}</h2>${content}</section>`;
    const identity = `<div class="cv-template-identity">${photo}<div class="cv-template-contact"><h1>${escapePreviewText(fullName)}</h1><div><strong>Passport:</strong> ${escapePreviewText(p.passport || '[PASSPORT NUMBER]')} &nbsp;&nbsp; <strong>Nationality:</strong> ${escapePreviewText(nationality || '[NATIONALITY]')}</div><div><strong>Date of birth:</strong> ${escapePreviewText(p.date_of_birth || '[DD/MM/YYYY]')} &nbsp;&nbsp; <strong>Gender:</strong> ${escapePreviewText(p.gender || '[GENDER]')}</div><div><strong>Phone number:</strong> ${escapePreviewText(p.phone || '[PHONE]')} &nbsp;&nbsp; <strong>Email:</strong> ${escapePreviewText(p.email || '[EMAIL]')}</div><div><strong>Home:</strong> ${escapePreviewText(address || '[ADDRESS]')}</div></div><div class="preview-brand"><img src="assets/eu-flag.svg" alt="European Union flag"><span>europass</span></div></div>`;
    const additionalWork = (cv.work_experience || []).slice(2).map(item => `<article class="cv-entry"><h3>${escapePreviewText(item.employer)}</h3><strong>${escapePreviewText(item.title)}</strong><div class="cv-entry-meta"><span>${escapePreviewText(item.start_date)} - ${escapePreviewText(item.end_date || 'CURRENT')}</span></div><p>${escapePreviewText(item.description || '')}</p></article>`).join('');
    const pageOne = `<div class="euro-page page-1 page"><div class="preview-stripe top stripe"></div><div class="preview-stripe bottom stripe"></div><div class="preview-corner top-left corner"></div><div class="preview-corner top-right corner"></div><div class="preview-corner bottom-left corner"></div><div class="preview-corner bottom-right corner"></div><div class="cv-template-content cv-template-page-one"><div class="header">${identity}</div>${section('ABOUT ME', `<p>${escapePreviewText(cv.about_me || 'Write a concise professional profile here.')}</p>`)}${section('EDUCATION AND TRAINING', education)}${section('WORK EXPERIENCE', work)}</div></div>`;
    const motherTongues = (cv.mother_tongues || []).map(escapePreviewText).join(', ') || '[LANGUAGE]';
    const skills = (cv.digital_skills || []).map(escapePreviewText).join(' / ') || '[SKILLS]';
    const hobbies = (cv.hobbies || []).map(item => `<div>${escapePreviewText(item)}</div>`).join('') || '[HOBBIES]';
    const closing = cv.other_info || 'Write the final career or study objective here.';
    const pageTwo = `<div class="euro-page page-2 page"><div class="preview-stripe top stripe"></div><div class="preview-stripe bottom stripe"></div><div class="preview-corner top-left corner"></div><div class="preview-corner top-right corner"></div><div class="preview-corner bottom-left corner"></div><div class="preview-corner bottom-right corner"></div><div class="cv-template-content cv-template-page-two">${section('LANGUAGE SKILLS', `<p><strong>Mother tongue(s):</strong> ${motherTongues}</p>${languages}`)}${section('SKILLS', `<div class="skill-group"><div class="skill-title">DIGITAL &amp; TECHNICAL SKILLS</div><p>${skills}</p></div>`)}${section('HOBBIES AND INTERESTS', hobbies)}${additionalWork ? section('ADDITIONAL WORK EXPERIENCE', additionalWork) : ''}${cv.other_info ? section('ADDITIONAL DETAILS', `<p>${escapePreviewText(cv.other_info)}</p>`) : ''}<div class="closing preview-closing">${escapePreviewText(closing)}<div class="date">[CITY], [DD/MM/YYYY]</div></div></div></div>`;
    return pageOne + pageTwo;
}

// Render the 8 Core Sections in the Right Column Accordion
function renderManualEditor(cv) {
    if (!editorBox) return;
    cv = cv || {};
    const p = cv.personal_info || {};

    const eduJson = JSON.stringify(cv.education || [], null, 2);
    const workJson = JSON.stringify(cv.work_experience || [], null, 2);
    const langJson = JSON.stringify(cv.other_languages || [], null, 2);
    const hobbyJson = JSON.stringify(cv.hobbies || [], null, 2);

    const nationalityVal = Array.isArray(p.nationality) ? p.nationality.join(', ') : (p.nationality || '');
    const skillsVal = Array.isArray(cv.digital_skills) ? cv.digital_skills.join(', ') : (cv.digital_skills || '');
    const addressVal = typeof p.address === 'object' && p.address !== null ? (p.address.city || p.address.line1 || '') : (p.address || '');

    const sections = [
        {
            title: "1. Personal Information & Header",
            id: "personal",
            content: `
                <div class="editor-field-group"><label>First Name</label><input type="text" id="edit_fn" value="${p.first_name || ''}"></div>
                <div class="editor-field-group"><label>Last Name</label><input type="text" id="edit_ln" value="${p.last_name || ''}"></div>
                <div class="editor-field-group"><label>Passport</label><input type="text" id="edit_passport" value="${p.passport || ''}"></div>
                <div class="editor-field-group"><label>Nationality</label><input type="text" id="edit_nat" value="${nationalityVal}"></div>
                <div class="editor-field-group"><label>Date of Birth</label><input type="text" id="edit_dob" value="${p.date_of_birth || ''}"></div>
                <div class="editor-field-group"><label>Gender</label><input type="text" id="edit_gender" value="${p.gender || ''}"></div>
                <div class="editor-field-group"><label>Phone</label><input type="text" id="edit_phone" value="${p.phone || ''}"></div>
                <div class="editor-field-group"><label>Email</label><input type="text" id="edit_email" value="${p.email || ''}"></div>
                <div class="editor-field-group"><label>Address</label><input type="text" id="edit_address" value="${addressVal}"></div>
                <button class="save-section-btn" data-section-id="personal">Apply Changes</button>
            `
        },
        {
            title: "2. About Me",
            id: "aboutme",
            content: `
                <div class="editor-field-group"><label>Profile Summary / Purpose</label><textarea id="edit_aboutme">${cv.about_me || ''}</textarea></div>
                <button class="save-section-btn" data-section-id="aboutme">Apply Changes</button>
            `
        },
        {
            title: "3. Education and Training",
            id: "education",
            content: `
                <div class="editor-field-group"><label>Degrees / Training (JSON format)</label><textarea id="edit_edu">${eduJson}</textarea></div>
                <button class="save-section-btn" data-section-id="education">Apply Changes</button>
            `
        },
        {
            title: "4. Work Experience & Internships",
            id: "work",
            content: `
                <div class="editor-field-group"><label>Experience Details (JSON format)</label><textarea id="edit_work">${workJson}</textarea></div>
                <button class="save-section-btn" data-section-id="work">Apply Changes</button>
            `
        },
        {
            title: "5. Language Skills",
            id: "languages",
            content: `
                <div class="editor-field-group"><label>Languages (JSON format)</label><textarea id="edit_lang">${langJson}</textarea></div>
                <button class="save-section-btn" data-section-id="languages">Apply Changes</button>
            `
        },
        {
            title: "6. Skills (Domain & Technical)",
            id: "skills",
            content: `
                <div class="editor-field-group"><label>Digital Skills (comma separated)</label><input type="text" id="edit_skills" value="${skillsVal}"></div>
                <button class="save-section-btn" data-section-id="skills">Apply Changes</button>
            `
        },
        {
            title: "7. Additional Information",
            id: "other_info",
            content: `
                <div class="editor-field-group"><label>Additional Details / Volunteering</label><textarea id="edit_other_info">${cv.other_info || ''}</textarea></div>
                <button class="save-section-btn" data-section-id="other_info">Apply Changes</button>
            `
        },
        {
            title: "8. Hobbies and Interests",
            id: "hobbies",
            content: `
                <div class="editor-field-group"><label>Interests (JSON format)</label><textarea id="edit_hobbies">${hobbyJson}</textarea></div>
                <button class="save-section-btn" data-section-id="hobbies">Apply Changes</button>
            `
        }
    ];

    editorBox.innerHTML = "";
    sections.forEach((sec, idx) => {
        const accordion = document.createElement('div');
        accordion.classList.add('section-accordion');
        accordion.innerHTML = `
            <div class="section-title-bar">
                <span>${sec.title}</span>
                <span>▼</span>
            </div>
            <div class="section-content-pane ${idx === 0 ? 'active' : ''}">
                ${sec.content}
            </div>
        `;
        editorBox.appendChild(accordion);
    });

    editorBox.querySelectorAll('.section-title-bar').forEach((bar) => {
        bar.addEventListener('click', () => toggleAccordion(bar));
    });
    editorBox.querySelectorAll('.save-section-btn').forEach((button) => {
        button.addEventListener('click', () => saveSection(button.dataset.sectionId));
    });

    editorBox.querySelectorAll('input, textarea').forEach((field) => {
        field.addEventListener('input', () => previewEditorChanges(field));
    });
}

function toggleAccordion(bar) {
    const pane = bar.nextElementSibling;
    pane.classList.toggle('active');
}

function previewEditorChanges(field) {
    if (!currentLoadedCV) return;

    const value = field.value;
    const fieldId = field.id;
    const personalInfo = currentLoadedCV.personal_info || {};

    const personalFields = {
        edit_fn: 'first_name',
        edit_ln: 'last_name',
        edit_passport: 'passport',
        edit_dob: 'date_of_birth',
        edit_gender: 'gender',
        edit_phone: 'phone',
        edit_email: 'email'
    };

    if (personalFields[fieldId]) {
        personalInfo[personalFields[fieldId]] = value;
    } else if (fieldId === 'edit_nat') {
        personalInfo.nationality = value.split(',').map(item => item.trim()).filter(Boolean);
    } else if (fieldId === 'edit_address') {
        personalInfo.address = {
            ...(typeof personalInfo.address === 'object' && personalInfo.address ? personalInfo.address : {}),
            line1: value
        };
    } else if (fieldId === 'edit_aboutme') {
        currentLoadedCV.about_me = value;
    } else if (fieldId === 'edit_skills') {
        currentLoadedCV.digital_skills = value.split(',').map(item => item.trim()).filter(Boolean);
    } else {
        const jsonFields = {
            edit_edu: 'education',
            edit_work: 'work_experience',
            edit_lang: 'other_languages',
            edit_hobbies: 'hobbies'
        };
        if (jsonFields[fieldId]) {
            try {
                currentLoadedCV[jsonFields[fieldId]] = JSON.parse(value);
            } catch {
                return;
            }
        } else if (fieldId === 'edit_other_info') {
            currentLoadedCV.other_info = value;
        }
    }

    currentLoadedCV.personal_info = personalInfo;
    cvPreviewContent.innerHTML = renderTemplatePreview(currentLoadedCV);
}

async function saveSection(sectionId) {
    if (!currentLoadedCV) return;
    currentLoadedCV.personal_info = currentLoadedCV.personal_info || {};
    
    if (sectionId === 'personal') {
        currentLoadedCV.personal_info.first_name = document.getElementById('edit_fn').value;
        currentLoadedCV.personal_info.last_name = document.getElementById('edit_ln').value;
        currentLoadedCV.personal_info.passport = document.getElementById('edit_passport').value;
        currentLoadedCV.personal_info.nationality = [document.getElementById('edit_nat').value];
        currentLoadedCV.personal_info.date_of_birth = document.getElementById('edit_dob').value;
        currentLoadedCV.personal_info.gender = document.getElementById('edit_gender').value;
        currentLoadedCV.personal_info.phone = document.getElementById('edit_phone').value;
        currentLoadedCV.personal_info.email = document.getElementById('edit_email').value;
        const addressValue = document.getElementById('edit_address').value.trim();
        const existingAddress = currentLoadedCV.personal_info.address || {};
        currentLoadedCV.personal_info.address = {
            ...(typeof existingAddress === 'object' ? existingAddress : {}),
            line1: addressValue
        };
    } else if (sectionId === 'aboutme') {
        currentLoadedCV.about_me = document.getElementById('edit_aboutme').value;
    } else if (sectionId === 'skills') {
        currentLoadedCV.digital_skills = document.getElementById('edit_skills').value.split(',').map(s => s.trim()).filter(Boolean);
    } else {
        try {
            if (sectionId === 'education') currentLoadedCV.education = JSON.parse(document.getElementById('edit_edu').value);
            if (sectionId === 'work') currentLoadedCV.work_experience = JSON.parse(document.getElementById('edit_work').value);
            if (sectionId === 'languages') currentLoadedCV.other_languages = JSON.parse(document.getElementById('edit_lang').value);
            if (sectionId === 'other_info') currentLoadedCV.other_info = document.getElementById('edit_other_info').value;
            if (sectionId === 'hobbies') currentLoadedCV.hobbies = JSON.parse(document.getElementById('edit_hobbies').value);
        } catch (e) {
            alert("Invalid JSON format in text area. Please check your syntax.");
            return;
        }
    }

    updateLivePreview(currentLoadedCV);
    
    try {
        await persistCurrentCV();
    } catch (error) {
        alert(error.message);
    }
}

async function persistCurrentCV() {
    if (!sessionId || !currentLoadedCV) return;

    const response = await fetch("/api/session/update-cv", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, cv: currentLoadedCV })
    });
    if (!response.ok) throw new Error("The CV could not be saved.");

    const data = await response.json();
    if (data.cv) {
        currentLoadedCV = data.cv;
        updateLivePreview(data.cv);
    }
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

        await persistCurrentCV();
        await exportPreviewPdf('Europass_CV.pdf');
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

async function exportPreviewPdf(filename = 'Europass_CV_Preview.pdf') {
    const element = document.getElementById('cvPreviewContent');
    if (!element || element.innerText.includes("Your live CV summary will appear here")) {
        alert("No CV content available to download yet!");
        return;
    }

    const options = {
        margin:       0,
        filename,
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { 
            scale: 2, 
            useCORS: true, 
            letterRendering: true,
            backgroundColor: null 
        },
        jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' },
        pagebreak:    { mode: ['css'] }
    };

    element.classList.add('pdf-export');

    try {
        await html2pdf().from(element).set(options).save();
    } finally {
        element.classList.remove('pdf-export');
    }
}

async function downloadLivePreviewPDF() {
    await persistCurrentCV();
    await exportPreviewPdf('Europass_CV_Preview.pdf');
}