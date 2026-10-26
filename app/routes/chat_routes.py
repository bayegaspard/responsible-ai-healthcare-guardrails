import logging
import os

from flask import Blueprint, render_template, request, redirect, url_for
import ollama
from nemoguardrails import LLMRails, RailsConfig

from policies import SYSTEM_PROMPT, evaluate

log = logging.getLogger(__name__)

# Blueprint setup
chat_bp = Blueprint('chat', __name__)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Ollama address for both models. Use 127.0.0.1 rather than "localhost": on some
# machines localhost resolves to a different server on the same port, such as a
# Docker Ollama container without the models.
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
if not OLLAMA_HOST.startswith("http"):
    OLLAMA_HOST = "http://" + OLLAMA_HOST
CHAT_MODEL = os.environ.get("CHAT_MODEL", "llama3.1")
GUARD_MODEL = os.environ.get("GUARD_MODEL", "llama3")

# Load the NeMo Guardrails config, then point it at the same Ollama server.
CONFIG_PATH = os.environ.get("GUARDRAILS_CONFIG", os.path.join(ROOT, "guardrails"))
config = RailsConfig.from_path(CONFIG_PATH)
for model in config.models:
    if model.type == "main":
        model.model = GUARD_MODEL
        model.parameters = {**(model.parameters or {}), "base_url": OLLAMA_HOST + "/v1"}
rails = LLMRails(config)

ollama_client = ollama.Client(host=OLLAMA_HOST)


def check_models():
    """Print a clear warning at startup if Ollama or a model is missing."""
    try:
        names = {m.model for m in ollama_client.list().models}
    except Exception as exc:
        print(f"\n[warning] Cannot reach Ollama at {OLLAMA_HOST}: {exc}\n"
              "          Start the Ollama app, or set OLLAMA_HOST.\n")
        return
    for wanted in (CHAT_MODEL, GUARD_MODEL):
        if not any(n == wanted or n.startswith(wanted + ":") for n in names):
            print(f"\n[warning] Model '{wanted}' is not in Ollama at {OLLAMA_HOST}. "
                  f"Run: ollama pull {wanted}\n")


check_models()

REFUSAL = ("I can't help with that request. It conflicts with the responsible AI "
           "policies for this clinical assistant.")


def nemo_input_blocked(message):
    """Run only the NeMo input rails. Returns True when a rail stops the message."""
    result = rails.generate(
        messages=[{"role": "user", "content": message}],
        options={"rails": ["input"], "log": {"activated_rails": True}},
    )
    return any(r.stop for r in result.log.activated_rails)


@chat_bp.route('/')
def index():
    return render_template('chat.html')


@chat_bp.route('/chat', methods=['GET', 'POST'])
def chat():
    if request.method == 'GET':
        return redirect(url_for('chat.index'))

    user_message = (request.form.get("message") or "").strip()
    guardrails_on = request.form.get("guardrails", "on") != "off"
    if not user_message:
        return {"error": "Empty message."}, 400

    try:
        if not guardrails_on:
            # Demo contrast: the raw model, with no policies, redaction, or system prompt.
            reply = ollama_client.chat(model=CHAT_MODEL,
                                       messages=[{"role": "user", "content": user_message}])
            decision = {"status": "off", "layer": None, "policies": [], "redactions": [],
                        "message": user_message, "trace": [
                            {"layer": "Policy engine", "result": "skipped"},
                            {"layer": "NeMo self-check", "result": "skipped"},
                            {"layer": "Model", "result": "answered without safeguards"}]}
            return {"response": reply["message"]["content"], "decision": decision}, 200

        # Layer 1: deterministic healthcare policies (block, redact, or add safeguards).
        decision = evaluate(user_message)
        trace = [{"layer": "Policy engine", "result": decision["status"] if decision["policies"] else "passed"}]
        if decision["status"] == "blocked":
            trace += [{"layer": "NeMo self-check", "result": "not needed"},
                      {"layer": "Model", "result": "never called"}]
            decision["trace"] = trace
            return {"response": REFUSAL, "decision": decision}, 200

        # Layer 2: NeMo Guardrails LLM self-check on the redacted message.
        if nemo_input_blocked(decision["message"]):
            decision.update(status="blocked", layer="NeMo Guardrails self-check", policies=[{
                "id": "NEMO", "title": "LLM input self-check", "principle": "Guardrails",
                "reason": "The guardrail model judged this request unsafe."}])
            trace += [{"layer": "NeMo self-check", "result": "blocked"},
                      {"layer": "Model", "result": "never called"}]
            decision["trace"] = trace
            return {"response": REFUSAL, "decision": decision}, 200
        trace.append({"layer": "NeMo self-check", "result": "passed"})

        # Layer 3: answer with the system prompt plus any required safeguards.
        system = SYSTEM_PROMPT
        if decision["guidance"]:
            system += "\n\nRequired safeguards for this answer:\n- " + "\n- ".join(decision["guidance"])
        reply = ollama_client.chat(
            model=CHAT_MODEL,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": decision["message"]}],
        )
        trace.append({"layer": "Model", "result": "answered with safeguards" if decision["guidance"] else "answered"})
        decision["trace"] = trace
        return {"response": reply["message"]["content"], "decision": decision}, 200
    except Exception as exc:  # surface model/server problems to the UI
        log.exception("Chat request failed")
        return {"error": f"Model call failed: {exc}"}, 502
