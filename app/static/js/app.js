const chatForm = document.getElementById("chat-form");
const chatLog = document.getElementById("chat-log");
const input = document.getElementById("user-message");
const toggle = document.getElementById("guardrails-toggle");
let lastMessage = "";

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

// Model replies are Markdown. Render them with the bundled marked library and
// sanitize the HTML with DOMPurify. Everything else stays plain text.
const canRenderMarkdown = typeof marked !== "undefined" && typeof DOMPurify !== "undefined";
if (canRenderMarkdown) marked.setOptions({ gfm: true, breaks: false });

function renderMarkdown(target, text) {
    // Ollama often indents sub-bullets with tabs; normalize them to spaces.
    const source = text.replace(/\t/g, "    ");
    target.innerHTML = DOMPurify.sanitize(marked.parse(source), {
        FORBID_TAGS: ["style", "img", "iframe", "form", "input"],
    });
    target.querySelectorAll("a").forEach((a) => {
        a.target = "_blank";
        a.rel = "noopener noreferrer";
    });
    target.classList.add("markdown");
}

// User text and errors go through textContent so they are never parsed as HTML.
function addMessage(role, text, opts = {}) {
    document.getElementById("empty-state")?.remove();
    const msg = el("div", `chat-message ${role}` + (opts.extraClass ? ` ${opts.extraClass}` : ""));
    const head = el("div", "message-head");
    head.append(el("span", "message-label", role === "user" ? "You" : "WallBridge AI"));
    if (opts.status) head.append(el("span", `pill pill-${opts.status}`, STATUS_LABEL[opts.status]));
    const body = el("div", "message-body");
    if (text !== null) {
        if (opts.markdown && canRenderMarkdown) renderMarkdown(body, text);
        else body.textContent = text;
    }
    msg.append(head, body);
    if (opts.reason) msg.append(el("div", "message-reason", opts.reason));
    if (opts.note) msg.append(el("div", "message-note", opts.note));
    chatLog.appendChild(msg);
    chatLog.scrollTop = chatLog.scrollHeight;
    return msg;
}

function syncMode() {
    const on = toggle.checked;
    document.body.classList.toggle("guardrails-off", !on);
    document.getElementById("guard-state").textContent = on ? "On" : "Off";
    document.getElementById("mode-note").textContent = on
        ? "Guardrails on: policy engine, NeMo self-check, then the model."
        : "Guardrails off: messages go straight to the raw model.";
    input.focus();
}
toggle.addEventListener("change", syncMode);
syncMode();

async function send(userMessage) {
    const guardrails = toggle.checked ? "on" : "off";
    lastMessage = userMessage;
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
        const p = (d.policies || [])[0];
        addMessage("system", data.response, {
            status: d.status,
            reason: p ? `${p.id} · ${p.reason}` : undefined,
            note: d.redactions && d.redactions.length ? "Sent to the model as: " + d.message : undefined,
            extraClass: d.status === "blocked" ? "blocked" : (d.status === "off" ? "unguarded" : ""),
            markdown: true,
        });
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

// Up arrow in an empty input recalls the last message, to resend after flipping the toggle.
input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowUp" && !input.value && lastMessage) {
        e.preventDefault();
        input.value = lastMessage;
    }
});

document.getElementById("clear-chat").addEventListener("click", () => {
    chatLog.replaceChildren();
    const empty = el("div", "empty-state");
    empty.id = "empty-state";
    empty.append(el("p", "", "Ask anything. Toggle guardrails to compare."));
    chatLog.append(empty);
    input.focus();
});
