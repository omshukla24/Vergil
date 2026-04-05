/* ========================================
   Vergil Command Center — Dashboard Logic v2
   ======================================== */

const API_BASE = "http://localhost:8000";
let events = [];
let stats = { total: 0, approved: 0, pending: 0, quorums: 0 };

// — Engine health check —
async function checkEngine() {
    const dot = document.getElementById("statusDot");
    const text = document.getElementById("statusText");
    try {
        const res = await fetch(`${API_BASE}/docs`, { method: "HEAD" });
        if (res.ok) {
            dot.classList.remove("offline");
            text.textContent = "Online";
        } else throw new Error();
    } catch {
        dot.classList.add("offline");
        text.textContent = "Offline";
    }
}

setInterval(checkEngine, 5000);
checkEngine();

// — Stats update —
function updateStats() {
    animateValue("metricTotal", stats.total);
    animateValue("metricApproved", stats.approved);
    animateValue("metricPending", stats.pending);
    animateValue("metricQuorums", stats.quorums);
}

function animateValue(id, target) {
    const el = document.getElementById(id);
    const current = parseInt(el.textContent) || 0;
    if (current === target) return;
    el.textContent = target;
    el.style.transition = "none";
    el.style.transform = "translateY(-2px)";
    el.style.opacity = "0.5";
    requestAnimationFrame(() => {
        el.style.transition = "all 200ms ease";
        el.style.transform = "translateY(0)";
        el.style.opacity = "1";
    });
}

// — Event feed —
function addEvent(type, content) {
    events.unshift({ type, content, time: new Date() });
    renderFeed();
}

function renderFeed() {
    const feed = document.getElementById("feed");
    const empty = document.getElementById("feedEmpty");
    const count = document.getElementById("feedCount");

    if (events.length === 0) {
        if (empty) empty.style.display = "block";
        count.textContent = "0 events";
        return;
    }

    if (empty) empty.style.display = "none";
    count.textContent = `${events.length} event${events.length !== 1 ? 's' : ''}`;

    // Keep only event elements, remove empty
    const html = events.map(e => {
        const t = e.time.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
        return `<div class="event">
            <div class="event-header">
                <span class="event-badge ${e.type}">${e.type.replace('-', ' ')}</span>
                <span class="event-time">${t}</span>
            </div>
            <div class="event-body">${e.content}</div>
        </div>`;
    }).join("");

    feed.innerHTML = html;
}

function clearFeed() {
    events = [];
    stats = { total: 0, approved: 0, pending: 0, quorums: 0 };
    updateStats();
    const feed = document.getElementById("feed");
    feed.innerHTML = `<div class="feed-empty" id="feedEmpty">
        <div class="feed-empty-icon">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
        </div>
        No events yet. Click a scenario to begin.
    </div>`;
    document.getElementById("feedCount").textContent = "0 events";
    resetStateMachine();
}

// — State Machine —
function setStateMachine(state) {
    const nodes = ["stateIdle", "stateGate", "stateExec", "statePend", "stateApproved"];
    nodes.forEach(n => {
        const el = document.getElementById(n);
        el.classList.remove("active", "success", "warning");
    });

    document.getElementById("stateIdle").classList.add("active");

    if (state === "gate" || state === "exec" || state === "pending" || state === "approved") {
        document.getElementById("stateGate").classList.add("active");
    }
    if (state === "exec") {
        document.getElementById("stateExec").classList.add("success");
    }
    if (state === "pending") {
        document.getElementById("statePend").classList.add("warning");
    }
    if (state === "approved") {
        document.getElementById("statePend").classList.add("warning");
        document.getElementById("stateApproved").classList.add("success");
    }
}

function resetStateMachine() {
    const nodes = ["stateIdle", "stateGate", "stateExec", "statePend", "stateApproved"];
    nodes.forEach(n => {
        const el = document.getElementById(n);
        el.classList.remove("active", "success", "warning");
    });
    document.getElementById("stateIdle").classList.add("active");
}

// — Scenarios —
async function executeScenario(level) {
    if (level === "low") {
        const action = "Block source IP 192.168.1.100 at firewall.";
        const confidence = 0.95;
        addEvent("execute", `<strong>${action}</strong><br/>Confidence: <strong>${confidence}</strong> | Threshold: <strong>0.90</strong> | User: soc_admin@company.com`);
        setStateMachine("gate");
        await executeAction(action, confidence, 0.90, "soc_admin@company.com");
    } else if (level === "high") {
        const action = "Isolate engineering VLAN.";
        const confidence = 0.75;
        addEvent("execute", `<strong>${action}</strong><br/>Confidence: <strong>${confidence}</strong> | Threshold: <strong>0.90</strong> | User: soc_admin@company.com`);
        setStateMachine("gate");
        await executeAction(action, confidence, 0.90, "soc_admin@company.com");
    } else if (level === "critical") {
        const action = "Wipe affected DB drives and failover to standby.";
        addEvent("execute", `<strong>${action}</strong><br/>Type: <strong>Quorum</strong> | Trustees: 3 | Required: 2`);
        await executeQuorum(action);
    }
}

async function executeAction(action, confidence, threshold, userId) {
    try {
        const res = await fetch(`${API_BASE}/api/v1/actions/execute`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action, confidence, threshold, user_id: userId })
        });
        const data = await res.json();
        stats.total++;

        if (data.status === "EXECUTABLE") {
            stats.approved++;
            setStateMachine("exec");
            addEvent("approved", `Action <strong>auto-approved</strong>. Confidence met threshold.<br/><span class="event-id">${data.action_id.slice(0, 12)}…</span>`);
        } else if (data.status === "PENDING") {
            stats.pending++;
            setStateMachine("pending");
            let content = `Action requires <strong>Step-Up Authentication</strong>.<br/><span class="event-id">${data.action_id.slice(0, 12)}…</span>`;
            if (data.auth_url) {
                content += `<a href="${data.auth_url}" target="_blank" class="event-url">${data.auth_url}</a>`;
            }
            addEvent("pending", content);
        }
        updateStats();
    } catch (err) {
        addEvent("denied", `<strong>Error:</strong> ${err.message}`);
    }
}

async function executeQuorum(action) {
    const trustees = ["ciso@company.com", "vp_eng@company.com", "oncall_lead@company.com"];
    try {
        const res = await fetch(`${API_BASE}/api/v1/actions/quorum`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action, trustees, required: 2 })
        });
        const data = await res.json();
        stats.total++;
        stats.quorums++;

        let trusteeHtml = "";
        if (data.auth_urls) {
            for (const [email, url] of Object.entries(data.auth_urls)) {
                trusteeHtml += `<div class="event-trustee">
                    <span class="event-trustee-email">${email}</span>
                    <a href="${url}" target="_blank" class="event-trustee-url">${url.slice(0, 70)}…</a>
                </div>`;
            }
        }

        addEvent("quorum", `Quorum created. Requires <strong>2-of-3</strong> approvals.<br/><span class="event-id">${data.action_id.slice(0, 12)}…</span><div class="event-trustees">${trusteeHtml}</div>`);

        setStateMachine("pending");
        updateStats();
    } catch (err) {
        addEvent("denied", `<strong>Error:</strong> ${err.message}`);
    }
}

// — Custom Action —
async function executeCustom() {
    const action = document.getElementById("customAction").value.trim();
    const confidence = parseFloat(document.getElementById("confSlider").value);
    const threshold = parseFloat(document.getElementById("threshSlider").value);
    const userId = document.getElementById("customUser").value.trim();

    if (!action) return;

    addEvent("execute", `<strong>${action}</strong><br/>Confidence: <strong>${confidence}</strong> | Threshold: <strong>${threshold}</strong> | User: ${userId}`);
    setStateMachine("gate");
    await executeAction(action, confidence, threshold, userId);
}
