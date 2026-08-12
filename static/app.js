let chatHistory = [];
let pendingEscalationData = null;
let lastQuestion = "";
let ttsEnabled = false;
let savedChats = [];
let currentChatId = Date.now();

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
function appendMessage(role, content, sources = null) {
    const chatBox = document.getElementById('chat-box');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    let safeContent = String(content || "");
    let html = `<div>${safeContent.replace(/\n/g, '<br>')}</div>`;

    if (role === 'bot' && sources && sources.length > 0) {
        const sourceId = 'src-' + Date.now();
        let sourcesHtml = sources.map((s, i) => `<b>${i+1}. ${s.title}</b><br><small>${s.category}</small><br>${s.content}`).join('<hr>');
        html += `<button class="sources-btn" onclick="toggleSources('${sourceId}')">📚 Retrieved Sources</button><div id="${sourceId}" class="sources-content">${sourcesHtml}</div>`;
    }
    if (role === 'bot' && content !== 'Thinking...') {
        const encQuestion = encodeURIComponent(lastQuestion).replace(/'/g, "%27");
        const encAnswer = encodeURIComponent(safeContent).replace(/'/g, "%27");

        html += `<div class="feedback-actions"><span onclick="sendFeedback('${encQuestion}', '${encAnswer}', 1)">👍</span><span onclick="sendFeedback('${encQuestion}', '${encAnswer}', 0)">👎</span></div>`;
    }

    msgDiv.innerHTML = html;
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
    return msgDiv;
}

function toggleSources(id) {
    const el = document.getElementById(id);
    el.style.display = el.style.display === 'block' ? 'none' : 'block';
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
            body: JSON.stringify({ question: text, history: chatHistory })
        });

        const data = await response.json();
        loadingMsg.remove();

        const relevantSources = (data.status === 'answered') ? data.sources : null;
        appendMessage('bot', data.answer, relevantSources);
        speakText(data.answer);

        chatHistory.push({ role: 'user', content: text });
        chatHistory.push({ role: 'assistant', content: data.answer });

        if (data.status === 'no_solution') {
            pendingEscalationData = { question: text, category: data.category };
            document.getElementById('escalation-ui').classList.remove('hidden');
            document.getElementById('input-area').classList.add('hidden');
        }
        saveCurrentSession();

    } catch (err) {
        console.error(err);
        loadingMsg.innerHTML = "Error connecting to server.";
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

async function sendFeedback(encQuestion, encAnswer, rating) {
    const question = decodeURIComponent(encQuestion);
    const answer = decodeURIComponent(encAnswer);
    await fetch('/api/feedback', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question, answer, rating }) });
    alert("Thank you for your feedback!");
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
        htmlContent: document.getElementById('chat-box').innerHTML
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
                    body: JSON.stringify({ questions: userQuestions })
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
}