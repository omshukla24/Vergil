/* ========================================
   Vergil Command Center — Dashboard Logic
   ======================================== */

const API_BASE = "http://localhost:8000";

// ── State ──
const state = {
    totalActions: 0,
    autoApproved: 0,
    pendingAuth: 0,
    quorums: 0,
    eventCount: 0,
    connected: false,
};

// ── DOM References ──
const els = {
    engineStatus: document.getElementById("engine-status"),
    statusText: document.querySelector("#engine-status .status-text"),
    statTotal: document.getElementById("stat-total-val"),
    statApproved: document.getElementById("stat-approved-val"),
    statPending: document.getElementById("stat-pending-val"),
    statQuorum: document.getElementById("stat-quorum-val"),
    feedContainer: document.getElementById("feed-container"),
    feedEmpty: document.getElementById("feed-empty"),
    feedCount: document.getElementById("feed-count"),
    confidenceSlider: document.getElementById("input-confidence-slider"),
    thresholdSlider: document.getElementById("input-threshold-slider"),
    confidenceDisplay: document.getElementById("confidence-display"),
    thresholdDisplay: document.getElementById("threshold-display"),
    customForm: document.getElementById("custom-action-form"),
    btnClear: document.getElementById("btn-clear-log"),
    btnExecute: document.getElementById("btn-execute"),
};

// ── State Machine Node IDs ──
const smNodes = ["sm-idle", "sm-gate", "sm-executable", "sm-pending", "sm-approved"];
const smArrows = ["sm-arrow-1", "sm-arrow-auto", "sm-arrow-auth", "sm-arrow-approve"];

// ── Utility Functions ──

function timestamp() {
    return new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function shortId(id) {
    return id ? id.substring(0, 8) + "..." : "n/a";
}

function updateStats() {
    animateStatValue(els.statTotal, state.totalActions);
    animateStatValue(els.statApproved, state.autoApproved);
    animateStatValue(els.statPending, state.pendingAuth);
    animateStatValue(els.statQuorum, state.quorums);
}

function animateStatValue(el, newVal) {
    if (el.textContent !== String(newVal)) {
        el.textContent = newVal;
        el.parentElement.parentElement.classList.remove("stat-bump");
        void el.parentElement.parentElement.offsetWidth; // trigger reflow
        el.parentElement.parentElement.classList.add("stat-bump");
    }
}

// ── State Machine Animation ──

function clearStateMachine() {
    smNodes.forEach(id => document.getElementById(id)?.classList.remove("active"));
    smArrows.forEach(id => document.getElementById(id)?.classList.remove("active"));
}

async function animateStateMachine(path) {
    clearStateMachine();
    for (const nodeId of path) {
        await sleep(400);
        const el = document.getElementById(nodeId);
        if (el) el.classList.add("active");
    }
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ── Feed Items ──

function addFeedItem(type, badgeClass, bodyHTML) {
    if (els.feedEmpty) {
        els.feedEmpty.style.display = "none";
    }

    state.eventCount++;
    els.feedCount.textContent = `${state.eventCount} events`;

    const item = document.createElement("div");
    item.className = "feed-item";
    item.innerHTML = `
        <div class="feed-item-header">
            <span class="feed-type-badge ${badgeClass}">${type}</span>
            <span class="feed-timestamp">${timestamp()}</span>
        </div>
        <div class="feed-item-body">${bodyHTML}</div>
    `;

    els.feedContainer.prepend(item);
}

// ── Health Check ──

async function checkEngineHealth() {
    try {
        const res = await fetch(`${API_BASE}/docs`, { method: "HEAD", mode: "no-cors" });
        state.connected = true;
        els.engineStatus.className = "status-indicator connected";
        els.statusText.textContent = "Engine Online";
    } catch {
        state.connected = false;
        els.engineStatus.className = "status-indicator disconnected";
        els.statusText.textContent = "Engine Offline";
    }
}

// ── API Calls ──

async function executeAction(action, confidence, threshold, userId) {
    state.totalActions++;
    updateStats();

    addFeedItem("EXECUTE", "badge-execute",
        `<strong>${action}</strong><br>Confidence: <strong>${confidence}</strong> | Threshold: <strong>${threshold}</strong> | User: ${userId}`
    );

    // Animate state machine: IDLE → GATE
    animateStateMachine(["sm-idle", "sm-arrow-1", "sm-gate"]);

    try {
        const res = await fetch(`${API_BASE}/api/v1/actions/execute`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action, confidence, threshold, user_id: userId }),
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${res.status}`);
        }

        const data = await res.json();

        if (data.status === "EXECUTABLE") {
            state.autoApproved++;
            updateStats();
            addFeedItem("AUTO-APPROVED", "badge-auto",
                `Action <strong>auto-approved</strong>. Confidence met threshold.<br>
                <span class="feed-action-id">ID: ${shortId(data.action_id)}</span>`
            );
            await animateStateMachine(["sm-idle", "sm-arrow-1", "sm-gate", "sm-arrow-auto", "sm-executable"]);
        } else if (data.status === "PENDING") {
            state.pendingAuth++;
            updateStats();
            let bodyHTML = `Action requires <strong>Step-Up Authentication</strong>.<br>
                <span class="feed-action-id">ID: ${shortId(data.action_id)}</span>`;
            if (data.auth_url) {
                bodyHTML += `<div class="feed-auth-url">🔗 ${data.auth_url}</div>`;
            }
            addFeedItem("STEP-UP REQUIRED", "badge-stepup", bodyHTML);
            await animateStateMachine(["sm-idle", "sm-arrow-1", "sm-gate", "sm-arrow-auth", "sm-pending"]);
        }

        return data;
    } catch (err) {
        addFeedItem("ERROR", "badge-error", `<strong>Request Failed:</strong> ${err.message}`);
        clearStateMachine();
        return null;
    }
}

async function executeQuorum(action, trustees, required) {
    state.totalActions++;
    state.quorums++;
    updateStats();

    addFeedItem("QUORUM INIT", "badge-quorum",
        `<strong>${action}</strong><br>Requires <strong>${required}-of-${trustees.length}</strong> approvals from: ${trustees.join(", ")}`
    );

    try {
        const res = await fetch(`${API_BASE}/api/v1/actions/quorum`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action, trustees, required }),
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${res.status}`);
        }

        const data = await res.json();
        let urlsHTML = '<div class="feed-quorum-urls">';
        if (data.auth_urls) {
            for (const [trustee, url] of Object.entries(data.auth_urls)) {
                urlsHTML += `<div class="trustee-url">
                    <span class="trustee-name">${trustee}</span>
                    <span class="trustee-link">${url.substring(0, 80)}...</span>
                </div>`;
            }
        }
        urlsHTML += "</div>";

        addFeedItem("QUORUM PENDING", "badge-quorum",
            `Quorum created. Awaiting ${required} trustee approvals.<br>
            <span class="feed-action-id">ID: ${shortId(data.action_id)}</span>
            ${urlsHTML}`
        );

        await animateStateMachine(["sm-idle", "sm-arrow-1", "sm-gate", "sm-arrow-auth", "sm-pending"]);

        return data;
    } catch (err) {
        addFeedItem("ERROR", "badge-error", `<strong>Quorum Request Failed:</strong> ${err.message}`);
        return null;
    }
}

// ── Event Handlers ──

// Scenario cards
document.getElementById("scenario-low").addEventListener("click", async function () {
    this.classList.add("active");
    await executeAction(
        "Block source IP 192.168.1.100 at firewall.",
        0.95, 0.90,
        "soc_admin@company.com"
    );
    setTimeout(() => this.classList.remove("active"), 2500);
});

document.getElementById("scenario-high").addEventListener("click", async function () {
    this.classList.add("active");
    await executeAction(
        "Isolate engineering VLAN.",
        0.75, 0.90,
        "soc_admin@company.com"
    );
    setTimeout(() => this.classList.remove("active"), 2500);
});

document.getElementById("scenario-critical").addEventListener("click", async function () {
    this.classList.add("active");
    await executeQuorum(
        "Wipe affected DB drives and failover to standby.",
        ["ciso@company.com", "vp_eng@company.com", "oncall_lead@company.com"],
        2
    );
    setTimeout(() => this.classList.remove("active"), 2500);
});

// Sliders
els.confidenceSlider.addEventListener("input", function () {
    els.confidenceDisplay.textContent = (this.value / 100).toFixed(2);
});

els.thresholdSlider.addEventListener("input", function () {
    els.thresholdDisplay.textContent = (this.value / 100).toFixed(2);
});

// Custom form
els.customForm.addEventListener("submit", async function (e) {
    e.preventDefault();
    const action = document.getElementById("input-action").value.trim();
    const confidence = parseFloat(els.confidenceSlider.value) / 100;
    const threshold = parseFloat(els.thresholdSlider.value) / 100;
    const userId = document.getElementById("input-user").value.trim() || "soc_admin@company.com";

    if (!action) return;

    els.btnExecute.disabled = true;
    els.btnExecute.textContent = "Executing...";

    await executeAction(action, confidence, threshold, userId);

    els.btnExecute.disabled = false;
    els.btnExecute.innerHTML = `<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M11.596 8.697l-6.363 3.692c-.54.313-1.233-.066-1.233-.697V4.308c0-.63.692-1.01 1.233-.696l6.363 3.692a.802.802 0 0 1 0 1.393z"/></svg> Execute Action`;
});

// Clear log
els.btnClear.addEventListener("click", function () {
    els.feedContainer.innerHTML = `<div class="feed-empty" id="feed-empty">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none" opacity="0.3">
            <circle cx="24" cy="24" r="20" stroke="currentColor" stroke-width="2"/>
            <path d="M24 14V28" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <circle cx="24" cy="34" r="2" fill="currentColor"/>
        </svg>
        <p>No events yet. Click a scenario card or execute a custom action.</p>
    </div>`;
    state.eventCount = 0;
    state.totalActions = 0;
    state.autoApproved = 0;
    state.pendingAuth = 0;
    state.quorums = 0;
    updateStats();
    clearStateMachine();
    els.feedCount.textContent = "0 events";
});

// ── Init ──

(async function init() {
    // Stagger-animate stats
    document.querySelectorAll(".stat-card").forEach((card, i) => {
        card.style.animationDelay = `${i * 100}ms`;
        card.classList.add("animate-in");
    });

    // Check engine health, repeat every 10s
    await checkEngineHealth();
    setInterval(checkEngineHealth, 10000);
})();
