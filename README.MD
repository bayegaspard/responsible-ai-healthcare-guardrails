### Responsible AI in Healthcare: Guardrails Demo

A clinical AI assistant that checks every request against healthcare policies before a local model answers. It's a live demo for the talk *Navigating AI Research Risk and Responsibility in Healthcare*, in collaboration with the University of Health and Allied Sciences, Ho.

Project page: https://bayegaspard.github.io/LauchAthon-team15/

#### How it works
1. **Policy engine** ([flask_app/policies.py](flask_app/policies.py)). Deterministic rules mapped to the talk's four principles block, redact, or attach a required safeguard.
2. **NeMo Guardrails self-check** ([team15/config](team15/config)). A local Llama 3 model judges anything the rules miss.
3. **Guided model**. Llama 3.1 answers with a clinical system prompt plus the required safeguards.

A **Guardrails On/Off** switch in the header sends the same message straight to the raw model, for comparison during the talk.

#### Run it
```bash
pip3 install -r requirements.txt
ollama pull llama3      # guardrail self-check
ollama pull llama3.1    # assistant
cd flask_app && python3 app.py
```
Then open http://127.0.0.1:5050. The app uses port 5050 because macOS AirPlay Receiver takes port 5000.

#### Settings
| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `5050` | Flask port |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama server for the assistant |
| `CHAT_MODEL` | `llama3.1` | Assistant model |
| `GUARDRAILS_CONFIG` | `team15/config` | NeMo Guardrails config folder |

The guardrail model's Ollama address is set in [team15/config/config.yml](team15/config/config.yml). Use `127.0.0.1` rather than `localhost` if Docker also runs an Ollama container on port 11434.

Use synthetic examples only. Never enter real patient data.
