let chatHistory = [];
let pendingEscalationData = null;
let lastQuestion = "";
let ttsEnabled = false;
let savedChats = [];
let currentChatId = Date.now();
let lastMessageDateStr = null;
let inactivityTimer = null;
let conversationClosed = false;
const INACTIVITY_TIMEOUT_MS = 10 * 1000;;

window.onload = () => {
    const storedChats = localStorage.getItem('telecom_saved_chats');
    if (storedChats) {
        savedChats = JSON.parse(storedChats);
        renderRecentChatsUI();
    }
};

function speakText(text) {
    if (!ttsEnabled || !('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const cleanText = text.replace(/<[^>]*>?/gm, '').replace(/[*_#]/g, '');
    const utterance = new SpeechSynthesisUtterance(cleanText);
    const isArabic = /[\u0600-\u06FF]/.test(cleanText);
    utterance.lang = isArabic ? 'ar-EG' : 'en-US';
    utterance.rate = 1.0;
    window.speechSynthesis.speak(utterance);
}

function toggleTTS() {
    ttsEnabled = !ttsEnabled;
    const btn = document.getElementById('tts-toggle');
    if (ttsEnabled) {
        btn.classList.remove('off');
    } else {
        btn.classList.add('off');
        window.speechSynthesis.cancel();
    }
}
function formatTime(date) {
    return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

function formatDateLabel(date) {
    const today = new Date();
    const yesterday = new Date();
    yesterday.setDate(today.getDate() - 1);
    if (date.toDateString() === today.toDateString()) return 'Today';
    if (date.toDateString() === yesterday.toDateString()) return 'Yesterday';
    return date.toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' });
}

function insertDateSeparatorIfNeeded(date) {
    const dateStr = date.toDateString();
    if (dateStr !== lastMessageDateStr) {
        lastMessageDateStr = dateStr;
        const chatBox = document.getElementById('chat-box');
        const sep = document.createElement('div');
        sep.className = 'date-separator';
        sep.innerHTML = `<span>${formatDateLabel(date)}</span>`;
        chatBox.appendChild(sep);
    }
}

function appendMessage(role, content, sources = null) {
    const chatBox = document.getElementById('chat-box');
    const timestamp = new Date();
    insertDateSeparatorIfNeeded(timestamp);
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;

    let safeContent = String(content || "");
    let html = `<div>${safeContent.replace(/\n/g, '<br>')}</div>`;
    if (role === 'bot' && sources && sources.length > 0) {
        const sourceId = 'src-' + Date.now();
        let sourcesHtml = sources.map((s, i) => `<b>${i+1}. ${s.title}</b><br><small>${s.category}</small><br>${s.content}`).join('<hr>');
        html += `<button class="sources-btn" onclick="toggleSources('${sourceId}')">📚 Retrieved Sources</button><div id="${sourceId}" class="sources-content">${sourcesHtml}</div>`;
    }
    if (role === 'bot' && content !== 'Thinking...' && !content.includes('⚠️')) {
        try {
            const base64Question = btoa(encodeURIComponent(lastQuestion || ""));
            const base64Answer = btoa(encodeURIComponent(safeContent));
            html += `<div class="feedback-actions">
                        <span onclick="sendFeedback('${base64Question}', '${base64Answer}', 1)">👍</span>
                        <span onclick="sendFeedback('${base64Question}', '${base64Answer}', 0)">👎</span>
                     </div>`;
        } catch(e) {
            console.error("Failed to render feedback buttons:", e);
        }
    }
    html += `<span class="msg-time">${formatTime(timestamp)}</span>`;
    msgDiv.innerHTML = html;
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
    return msgDiv;
}

function toggleSources(id) {
    const el = document.getElementById(id);
    el.style.display = el.style.display === 'block' ? 'none' : 'block';
}

function resetInactivityTimer() {
    if (inactivityTimer) {
        clearTimeout(inactivityTimer);
        inactivityTimer = null;
    }
    if (conversationClosed) return;
    inactivityTimer = setTimeout(() => {
        appendMessage('bot', 'Was the issue solved? (y/n)');
        speakText('Was the issue solved?');
    }, INACTIVITY_TIMEOUT_MS);
}

function stopInactivityTimer() {
    if (inactivityTimer) {
        clearTimeout(inactivityTimer);
        inactivityTimer = null;
    }
}


async function sendMessage() {
    const input = document.getElementById('user-input');
    const text = input.value.trim();
    if (!text) return;

    document.getElementById('welcome-screen').classList.add('hidden');
    document.getElementById('chat-box').classList.remove('hidden');

    lastQuestion = text;
    input.value = '';
    appendMessage('user', text);

    const loadingMsg = appendMessage('bot', 'Thinking...');

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: text, history: chatHistory,
                conversation_id: String(currentChatId)
             })
        });

        const data = await response.json();
        if (document.body.contains(loadingMsg)) {
            loadingMsg.remove();
        }

        const relevantSources = (data.status === 'answered') ? data.sources : null;
        appendMessage('bot', data.answer, relevantSources);
        try {
            speakText(data.answer);
        } catch(ttsErr) {
            console.warn("Text-to-speech failed:", ttsErr);
        }

        chatHistory.push({ role: 'user', content: text });
        chatHistory.push({ role: 'assistant', content: data.answer || "" });

        if (data.status === 'no_solution') {
            pendingEscalationData = { question: text, category: data.category };
            document.getElementById('escalation-ui').classList.remove('hidden');
            document.getElementById('input-area').classList.add('hidden');
        }

        if (data.status === 'resolved' || data.status === 'unresolved') {
            conversationClosed = true;
            stopInactivityTimer();
        } else {
            resetInactivityTimer();
        }
        saveCurrentSession();

    } catch (err) {
        console.error("Chat error:", err);
        if (document.body.contains(loadingMsg)) {
            loadingMsg.remove();
        }
        appendMessage('bot', '⚠️ Something went wrong! Please check the console (F12) for details.');
    }
}

async function submitEscalation() {
    const contact = document.getElementById('contact-input').value.trim();
    if (!contact) {
        alert("Please enter an email or phone number.");
        return;
    }
    const payload = { contact: contact, question: pendingEscalationData.question, category: pendingEscalationData.category, history: chatHistory };
    const response = await fetch('/api/escalate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const data = await response.json();
    if (data.success) {
        appendMessage('bot', data.message);
        speakText(data.message);
    } else {
        appendMessage('bot', "Failed to escalate issue.");
    }
    document.getElementById('escalation-ui').classList.add('hidden');
    document.getElementById('input-area').classList.remove('hidden');
    document.getElementById('contact-input').value = '';
    pendingEscalationData = null;
    saveCurrentSession();
}

function showToast(projectName, message) {
    let toast = document.getElementById('custom-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'custom-toast';
        toast.className = 'custom-toast';
        document.body.appendChild(toast);
    }
    toast.innerHTML = `
        <div class="toast-title">🔔 ${projectName}</div>
        <div class="toast-message">${message}</div>
    `;
    toast.classList.add('show');
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3500);
}
async function sendFeedback(b64Question, b64Answer, rating) {
    try {
        const question = decodeURIComponent(atob(b64Question));
        const answer = decodeURIComponent(atob(b64Answer));

        const response = await fetch('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, answer, rating })
        });
        if (response.ok) {
            showToast("Telecom AI", "Thank you for your feedback! It has been saved.");
        } else {
            showToast("Telecom AI Error", "Feedback failed. Check your server.");
        }
    } catch (err) {
        console.error("Feedback error:", err);
        showToast("Telecom AI Error", "Something went wrong! Check the console.");
    }
}

function handleKeyPress(e) {
    if (e.key === 'Enter') sendMessage();
}

function saveCurrentSession() {
    if (chatHistory.length === 0) return;
    const firstUserMsg = chatHistory.find(msg => msg.role === 'user');
    const chatTitle = firstUserMsg ? firstUserMsg.content.substring(0, 22) + "..." : "New Chat";
    const sessionData = {
        id: currentChatId,
        title: chatTitle,
        history: [...chatHistory],
        htmlContent: document.getElementById('chat-box').innerHTML,
        lastMessageDateStr: lastMessageDateStr,
        conversationClosed: conversationClosed
    };

    const existingIndex = savedChats.findIndex(chat => chat.id === currentChatId);
    if (existingIndex >= 0) {
        savedChats[existingIndex] = sessionData;
    } else {
        savedChats.unshift(sessionData);
    }
    localStorage.setItem('telecom_saved_chats', JSON.stringify(savedChats));
    renderRecentChatsUI();
}

function renderRecentChatsUI() {
    const list = document.getElementById('recent-chats-list');
    if (!list) return;

    list.innerHTML = '';

    if (savedChats.length === 0) {
        list.innerHTML = '<li style="cursor: default; background: transparent; color: #8a8593; display: block;">There are no chats yet</li>';
        return;
    }
    savedChats.forEach(chat => {
        const li = document.createElement('li');
        const titleSpan = document.createElement('span');
        titleSpan.className = 'chat-title-span';
        titleSpan.innerText = chat.title;

        const deleteBtn = document.createElement('button');
        deleteBtn.innerHTML = '🗑️';
        deleteBtn.className = 'delete-chat-btn';
        deleteBtn.title = "Delete Chat";

        deleteBtn.onclick = (e) => {
            e.stopPropagation();
            deleteChatSession(chat.id);
        };

        if (chat.id === currentChatId) {
            li.classList.add('active');
        }
        li.onclick = () => loadSavedSession(chat.id);
        li.appendChild(titleSpan);
        li.appendChild(deleteBtn);
        list.appendChild(li);
    });
}

async function deleteChatSession(id) {
    const confirmDelete = confirm("Are you sure you want to delete this chat?");
    if (!confirmDelete) return;
    const chatToDelete = savedChats.find(chat => chat.id === id);
    if (chatToDelete) {
        const userQuestions = chatToDelete.history
            .filter(msg => msg.role === 'user')
            .map(msg => msg.content);
        if (userQuestions.length > 0) {
            try {
                await fetch('/api/feedback/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ questions: userQuestions ,conversation_id: String(id)})
                });
            } catch (err) {
                console.error("Failed to delete feedback logs from server:", err);
            }
        }
    }
    savedChats = savedChats.filter(chat => chat.id !== id);
    localStorage.setItem('telecom_saved_chats', JSON.stringify(savedChats));
    if (id === currentChatId) {
        chatHistory = [];
        currentChatId = Date.now();
        lastQuestion = "";
        if ('speechSynthesis' in window) window.speechSynthesis.cancel();

        document.getElementById('chat-box').innerHTML = '';
        document.getElementById('chat-box').classList.add('hidden');
        document.getElementById('welcome-screen').classList.remove('hidden');
        document.getElementById('escalation-ui').classList.add('hidden');
        document.getElementById('input-area').classList.remove('hidden');
    }

    renderRecentChatsUI();
}
function clearChat() {
    if (chatHistory.length === 0) return;
    saveCurrentSession();
    chatHistory = [];
    currentChatId = Date.now();
    lastQuestion = "";
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    document.getElementById('chat-box').innerHTML = '';
    document.getElementById('chat-box').classList.add('hidden');
    document.getElementById('welcome-screen').classList.remove('hidden');
    document.getElementById('escalation-ui').classList.add('hidden');
    document.getElementById('input-area').classList.remove('hidden');

    renderRecentChatsUI();
}
function loadSavedSession(id) {
    if (id === currentChatId) return;
    if (chatHistory.length > 0) saveCurrentSession();
    const chatToLoad = savedChats.find(chat => chat.id === id);
    if (!chatToLoad) return;
    currentChatId = chatToLoad.id;
    chatHistory = [...chatToLoad.history];
    document.getElementById('chat-box').innerHTML = chatToLoad.htmlContent;
    document.getElementById('chat-box').classList.remove('hidden');
    document.getElementById('welcome-screen').classList.add('hidden');
    document.getElementById('escalation-ui').classList.add('hidden');
    document.getElementById('input-area').classList.remove('hidden');
    renderRecentChatsUI();
    const chatBox = document.getElementById('chat-box');
    chatBox.scrollTop = chatBox.scrollHeight;
     if (!conversationClosed) resetInactivityTimer();
}