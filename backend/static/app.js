const API_BASE = '';

const entryForm = document.getElementById('entryForm');
const showDataBtn = document.getElementById('showDataBtn');
const noonDataDiv = document.getElementById('noonData');
const contradictionChatDiv = document.getElementById('contradictionChat');
const chatHistoryDiv = document.getElementById('chatHistory');
const chatInput = document.getElementById('chatInput');
const sendChatBtn = document.getElementById('sendChat');

let contradictionState = null;
let chatHistory = [];

entryForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const entry = {
        Vessel_name: document.getElementById('vesselName').value,
        Date: document.getElementById('date').value,
        Laden_Ballst: document.getElementById('ladenBallast').value,
        Report_Type: document.getElementById('reportType').value
    };
    // Check contradiction
    const checkRes = await fetch(`/check_contradiction`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            vessel_name: entry.Vessel_name,
            new_laden_ballast: entry.Laden_Ballst,
            new_report_type: entry.Report_Type
        })
    }).then(r => r.json());
    if (checkRes.is_contradiction) {
        contradictionState = {
            entry,
            previous_status: checkRes.previous_status
        };
        contradictionChatDiv.style.display = 'block';
        chatHistory = [{ role: 'assistant', content: checkRes.reason || 'Contradiction detected. Please confirm or correct.' }];
        renderChat();
    } else {
        // Add entry directly
        await fetch(`/add_entry`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ entry })
        });
        alert('Entry added successfully!');
        contradictionChatDiv.style.display = 'none';
        contradictionState = null;
        chatHistory = [];
    }
});

showDataBtn.addEventListener('click', async () => {
    if (noonDataDiv.style.display === 'none') {
        const data = await fetch(`/get_noon_data`).then(r => r.json());
        renderNoonData(data.data);
        noonDataDiv.style.display = 'block';
    } else {
        noonDataDiv.style.display = 'none';
    }
});

sendChatBtn.addEventListener('click', async () => {
    const userMsg = chatInput.value;
    if (!userMsg) return;
    chatHistory.push({ role: 'user', content: userMsg });
    renderChat();
    chatInput.value = '';
    // Call chat_response API
    const res = await fetch(`/chat_response`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            conversation_history: chatHistory,
            vessel_name: contradictionState.entry.Vessel_name,
            previous_status: contradictionState.previous_status,
            new_status: contradictionState.entry.Laden_Ballst
        })
    }).then(r => r.json());
    chatHistory.push({ role: 'assistant', content: res.bot_response });
    renderChat();
    if (res.action === 'proceed') {
        // Add entry
        await fetch(`/add_entry`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ entry: contradictionState.entry })
        });
        alert('Data updated as requested!');
        contradictionChatDiv.style.display = 'none';
        contradictionState = null;
        chatHistory = [];
    } else if (res.action === 'correct' && res.corrected_status) {
        contradictionState.entry.Laden_Ballst = res.corrected_status;
        await fetch(`/add_entry`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ entry: contradictionState.entry })
        });
        alert(`Data updated to ${res.corrected_status} as requested!`);
        contradictionChatDiv.style.display = 'none';
        contradictionState = null;
        chatHistory = [];
    }
});

function renderChat() {
    chatHistoryDiv.innerHTML = '';
    chatHistory.forEach(msg => {
        const div = document.createElement('div');
        div.className = msg.role;
        div.textContent = `${msg.role === 'user' ? 'You' : 'Bot'}: ${msg.content}`;
        chatHistoryDiv.appendChild(div);
    });
}

function renderNoonData(data) {
    if (!data.length) {
        noonDataDiv.innerHTML = '<em>No data available.</em>';
        return;
    }
    let html = '<table class="table table-bordered"><thead><tr><th>Vessel</th><th>Date</th><th>Laden/Ballast</th><th>Report Type</th></tr></thead><tbody>';
    data.forEach(row => {
        html += `<tr><td>${row.Vessel_name}</td><td>${row.Date}</td><td>${row.Laden_Ballst}</td><td>${row.Report_Type}</td></tr>`;
    });
    html += '</tbody></table>';
    noonDataDiv.innerHTML = html;
}
