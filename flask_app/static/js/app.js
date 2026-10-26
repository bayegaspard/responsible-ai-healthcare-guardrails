const chatForm = document.getElementById("chat-form");
const chatLog = document.getElementById("chat-log");
const input = document.getElementById("user-message");
const toggle = document.getElementById("guardrails-toggle");
const trace = document.getElementById("trace");

const STATUS_LABEL = {
    allowed: "Allowed",
    safeguarded: "Safeguarded",
    redacted: "Redacted",
    blocked: "Blocked",
    off: "Guardrails off",
};

function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
}

// All message text goes through textContent so it is never parsed as HTML.
function addMessage(role, text, opts = {}) {
    document.getElementById("empty-state")?.remove();
    const msg = el("div", `chat-message ${role}` + (opts.extraClass ? ` ${opts.extraClass}` : ""));
    const head = el("div", "message-head");
    head.append(el("span", "message-label", role === "user" ? "You" : "WallBridge AI"));
    if (opts.status) head.append(el("span", `pill pill-${opts.status}`, STATUS_LABEL[opts.status]));
    if (opts.policies) opts.policies.forEach((p) => head.append(el("span", "pill pill-id", p.id)));
    const body = el("div", "message-body");
    if (text !== null) body.textContent = text;
    msg.append(head, body);
    if (opts.note) msg.append(el("div", "message-note", opts.note));
    chatLog.appendChild(msg);
    chatLog.scrollTop = chatLog.scrollHeight;
    return msg;
}

function renderTrace(decision) {
    trace.replaceChildren();
    const top = el("div", "trace-status");
    top.append(el("span", `pill pill-${decision.status}`, STATUS_LABEL[decision.status]));
    if (decision.layer) top.append(el("span", "trace-layer", "by " + decision.layer));
    trace.append(top);

    const steps = el("ol", "trace-steps");
    (decision.trace || []).forEach((t) => {
        const li = el("li", "trace-step result-" + t.result.split(" ")[0]);
        li.append(el("span", "step-name", t.layer), el("span", "step-result", t.result));
        steps.append(li);
    });
    trace.append(steps);

    (decision.policies || []).forEach((p) => {
        const r = el("div", "trace-reason");
        r.append(el("strong", "", `${p.id} · ${p.title}`), el("span", "", p.reason));
        trace.append(r);
    });

    document.querySelectorAll(".policy").forEach((n) => n.classList.remove("fired"));
    (decision.policies || []).forEach((p) => document.getElementById("policy-" + p.id)?.classList.add("fired"));
}

function syncMode() {
    const on = toggle.checked;
    document.body.classList.toggle("guardrails-off", !on);
    document.getElementById("guard-state").textContent = on ? "On" : "Off";
    document.getElementById("mode-note").textContent = on
        ? "Guardrails on: policy engine, NeMo self-check, then the model."
        : "Guardrails off: messages go straight to the raw model.";
}
toggle.addEventListener("change", syncMode);
syncMode();

async function send(userMessage) {
    const guardrails = toggle.checked ? "on" : "off";
    addMessage("user", userMessage, { status: guardrails === "off" ? "off" : undefined });
    input.value = "";
    input.disabled = true;

    const loading = addMessage("system", null, { extraClass: "loading-message" });
    loading.querySelector(".message-body").innerHTML =
        '<span class="typing-dots"><span></span><span></span><span></span></span>';

    try {
        const response = await fetch("/chat", {
            method: "POST",
            body: new URLSearchParams({ message: userMessage, guardrails }),
        });
        const data = await response.json();
        loading.remove();
        if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
        const d = data.decision;
        const note = d.redactions && d.redactions.length ? "Sent to the model as: " + d.message : undefined;
        addMessage("system", data.response, {
            status: d.status,
            policies: d.policies,
            extraClass: d.status === "blocked" ? "blocked" : (d.status === "off" ? "unguarded" : ""),
            note,
        });
        renderTrace(d);
    } catch (error) {
        loading.remove();
        addMessage("system", "Something went wrong: " + error.message, { extraClass: "error" });
        console.error("Error sending message:", error);
    } finally {
        input.disabled = false;
        input.focus();
    }
}

chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (text) send(text);
});

document.querySelectorAll(".scenario").forEach((btn) =>
    btn.addEventListener("click", () => {
        if (!input.disabled) send(btn.dataset.prompt);
    })
);

document.getElementById("clear-chat").addEventListener("click", () => {
    chatLog.replaceChildren();
    const empty = el("div", "empty-state");
    empty.id = "empty-state";
    empty.append(el("p", "", "Pick a scenario on the left or type your own question."));
    chatLog.append(empty);
    trace.replaceChildren(el("p", "panel-hint", "Send a message to see how each layer handled it."));
    document.querySelectorAll(".policy").forEach((n) => n.classList.remove("fired"));
});
