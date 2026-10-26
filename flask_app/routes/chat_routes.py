import logging
import os

from flask import Blueprint, render_template, request, redirect, url_for
import ollama
from nemoguardrails import LLMRails, RailsConfig

from policies import SYSTEM_PROMPT, evaluate

log = logging.getLogger(__name__)

# Blueprint setup
chat_bp = Blueprint('chat', __name__)

# Load NeMo Guardrails configuration (team15/config, unless overridden)
CONFIG_PATH = os.environ.get(
    "GUARDRAILS_CONFIG",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "team15", "config")),
)
config = RailsConfig.from_path(CONFIG_PATH)
rails = LLMRails(config)

# Talk to Ollama on 127.0.0.1 explicitly; "localhost" can resolve to a different
# server on the same port (e.g. a Docker Ollama container without the models).
ollama_client = ollama.Client(host=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"))
CHAT_MODEL = os.environ.get("CHAT_MODEL", "llama3.1")

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
