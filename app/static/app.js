let currentVolunteers = [];
let selectedVolunteer = null;

// Initialize when page loads
document.addEventListener("DOMContentLoaded", () => {
  loadDashboard();
  loadVolunteers();
});

// Quick Prompt Fill
function fillPrompt(text) {
  const input = document.getElementById("coordinatorInput");
  input.value = text;
  input.focus();
}

// Fetch dashboard state & table
async function loadDashboard() {
  try {
    const res = await fetch("/api/dashboard");
    const data = await res.json();
    renderKPIs(data.stats);
    renderTable(data.tasks);
  } catch (err) {
    console.error("Failed to load dashboard data:", err);
  }
}

// Load volunteers into phone dropdown
async function loadVolunteers() {
  try {
    const res = await fetch("/api/volunteers");
    const vols = await res.json();
    currentVolunteers = vols;
    const select = document.getElementById("volunteerSelect");
    select.innerHTML = "";
    vols.forEach(v => {
      const opt = document.createElement("option");
      opt.value = v.phone;
      opt.textContent = `${v.name} (${v.pillar || 'Tech'})`;
      select.appendChild(opt);
    });
    if (vols.length > 0) {
      switchVolunteerPhone(vols[0].phone);
    }
  } catch (err) {
    console.error("Failed to load volunteers:", err);
  }
}

// Switch active phone view
function switchVolunteerPhone(phone) {
  selectedVolunteer = currentVolunteers.find(v => v.phone === phone);
  if (selectedVolunteer) {
    document.getElementById("phoneVolunteerName").textContent = selectedVolunteer.name;
    document.getElementById("phoneVolunteerHandle").textContent = `@${selectedVolunteer.handle} &middot; ${selectedVolunteer.phone}`;
  }
}

// Render KPI Cards
function renderKPIs(stats) {
  if (!stats) return;
  document.getElementById("kpiTotal").textContent = stats.total_tasks || 0;
  document.getElementById("kpiProgress").textContent = stats.in_progress || 0;
  document.getElementById("kpiCompleted").textContent = stats.completed || 0;
  document.getElementById("kpiPending").textContent = stats.pending_or_sent || 0;
  document.getElementById("taskCountBadge").textContent = `${stats.total_tasks || 0} tasks`;
}

// Render Task Ledger Table
function renderTable(tasks) {
  const tbody = document.getElementById("taskTableBody");
  tbody.innerHTML = "";
  
  if (!tasks || tasks.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-state">No tasks assigned yet. Use the group chat on the left to assign one!</td></tr>`;
    return;
  }

  tasks.forEach(t => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${t.id}</strong></td>
      <td>${escapeHtml(t.title)}</td>
      <td>
        <strong>${escapeHtml(t.assignee_name)}</strong><br>
        <small style="color:#94a3b8">${t.assignee_phone}</small>
      </td>
      <td>${escapeHtml(t.deadline_text || 'N/A')}</td>
      <td><span class="priority-chip ${t.priority}">${t.priority}</span></td>
      <td><span class="status-chip ${t.status}">${t.status}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

// Send Coordinator Group Message
async function sendCoordinatorMessage(e) {
  e.preventDefault();
  const input = document.getElementById("coordinatorInput");
  const msg = input.value.trim();
  if (!msg) return;

  const feed = document.getElementById("groupChatFeed");

  // 1. Append Coordinator bubble
  const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const userBubble = document.createElement("div");
  userBubble.className = "chat-bubble coordinator";
  userBubble.innerHTML = `
    <div class="bubble-sender">Coordinator (Ryan)</div>
    <div class="bubble-content">${escapeHtml(msg)}</div>
    <div class="bubble-time">${timeStr}</div>
  `;
  feed.appendChild(userBubble);
  feed.scrollTop = feed.scrollHeight;

  input.value = "";

  // 2. Send to backend
  try {
    const res = await fetch("/api/simulate/coordinator", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg })
    });
    const data = await res.json();
    const result = data.result;

    // 3. Append Bot Receipt
    if (result.is_task) {
      const botBubble = document.createElement("div");
      botBubble.className = "chat-bubble bot-reply";
      
      let botText = "";
      if (result.status === "ASSIGNED") {
        botText = `📌 <strong>Task #${result.task.id}</strong> logged for <strong>@${result.volunteer.handle}</strong>. Details sent to ${result.volunteer.name.split(' ')[0]} via private WhatsApp DM.`;
        
        // Update Gemini extraction preview
        document.getElementById("extractionJson").textContent = JSON.stringify(result.extracted, null, 2);

        // Switch phone to this volunteer
        const select = document.getElementById("volunteerSelect");
        select.value = result.volunteer.phone;
        switchVolunteerPhone(result.volunteer.phone);

        // Add incoming DM to phone feed
        const phoneFeed = document.getElementById("volunteerChatFeed");
        const waMsg = document.createElement("div");
        waMsg.className = "wa-msg incoming";
        waMsg.innerHTML = `👋 <strong>Hi ${result.volunteer.name.split(' ')[0]}!</strong><br>` +
          `New task assigned by Coordinator:<br><br>` +
          `📋 <strong>Task:</strong> ${escapeHtml(result.task.title)}<br>` +
          `⏰ <strong>Deadline:</strong> ${escapeHtml(result.task.deadline_text)}<br>` +
          `🏷️ <strong>Category:</strong> ${result.task.category}<br><br>` +
          `Reply:<br>• <strong>1</strong> to Accept<br>• <strong>2</strong> if Unavailable<br>• Type <strong>Done</strong> when finished!`;
        phoneFeed.appendChild(waMsg);
        phoneFeed.scrollTop = phoneFeed.scrollHeight;

      } else {
        botText = `⚠️ ${escapeHtml(result.error || 'Could not assign task.')}`;
      }

      botBubble.innerHTML = `
        <div class="bubble-sender">Mtaani Bot 🤖</div>
        <div class="bubble-content">${botText}</div>
        <div class="bubble-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
      `;
      feed.appendChild(botBubble);
      feed.scrollTop = feed.scrollHeight;

      // Refresh table and KPIs
      loadDashboard();
    }
  } catch (err) {
    console.error("Coordinator message error:", err);
  }
}

// Send Volunteer 1-Touch or Custom Reply
async function sendVolunteerReply(actionText) {
  if (!selectedVolunteer) return;
  const phoneFeed = document.getElementById("volunteerChatFeed");

  // Outgoing user bubble in phone
  const outMsg = document.createElement("div");
  outMsg.className = "wa-msg outgoing";
  outMsg.textContent = actionText;
  phoneFeed.appendChild(outMsg);
  phoneFeed.scrollTop = phoneFeed.scrollHeight;

  // Post to backend
  try {
    const res = await fetch("/api/simulate/volunteer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        phone: selectedVolunteer.phone,
        message: actionText,
        sender_name: selectedVolunteer.name
      })
    });
    const data = await res.json();
    const result = data.result;

    // Incoming reply from bot in phone
    if (result && result.reply) {
      const inMsg = document.createElement("div");
      inMsg.className = "wa-msg incoming";
      inMsg.innerHTML = escapeHtml(result.reply).replace(/\n/g, "<br>").replace(/\*(.*?)\*/g, "<strong>$1</strong>");
      phoneFeed.appendChild(inMsg);
      phoneFeed.scrollTop = phoneFeed.scrollHeight;
    }

    // Refresh Dashboard table to reflect status change (e.g. ACKNOWLEDGED or COMPLETED)
    loadDashboard();
  } catch (err) {
    console.error("Volunteer reply error:", err);
  }
}

function submitVolunteerCustomReply(e) {
  e.preventDefault();
  const input = document.getElementById("volunteerCustomInput");
  const msg = input.value.trim();
  if (!msg) return;
  sendVolunteerReply(msg);
  input.value = "";
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
