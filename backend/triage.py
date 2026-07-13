import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

SYSTEM_PROMPT = (
    "You are a security analyst assistant embedded in a threat-detection dashboard. "
    "You are given one flagged network flow: its detected category, confidence, and raw "
    "flow features. Write a short triage note for a human analyst with exactly two parts:\n"
    "1. Why this was flagged — in plain language, referencing the specific field values given.\n"
    "2. Recommended next step — one concrete, bounded action (e.g. isolate host, block IP, "
    "review related flows, or 'likely benign, monitor' if the confidence is low).\n"
    "Keep it under 100 words total. No preamble, no markdown headers, just the two parts."
)

# The handful of raw UNSW-NB15 fields that are actually interpretable to a
# human analyst — dumping all 39 features would just be noise in the prompt.
INTERESTING_FIELDS = ["dur", "service", "state", "rate", "sttl", "dttl", "spkts", "dpkts", "sload", "dload"]


class TriageError(Exception):
    pass


def generate_triage(
    *,
    label: str,
    severity: str,
    score: float,
    source_ip: str,
    dest_ip: str,
    protocol: str,
    bytes_transferred: int,
    raw_features: dict,
) -> str:
    feature_lines = "\n".join(
        f"  {k}: {raw_features[k]}" for k in INTERESTING_FIELDS if k in raw_features
    )
    user_prompt = (
        f"Detected category: {label}\n"
        f"Severity: {severity}\n"
        f"Model confidence: {score:.0%}\n"
        f"Source IP: {source_ip}\n"
        f"Destination IP: {dest_ip}\n"
        f"Protocol: {protocol}\n"
        f"Bytes transferred: {bytes_transferred}\n"
        f"Flow features:\n{feature_lines}"
    )

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
            },
            timeout=60,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise TriageError(
            f"Couldn't reach Ollama at {OLLAMA_URL} — is it running? (`ollama serve`, "
            f"or `brew services start ollama`). Original error: {e}"
        )

    body = resp.json()
    content = body.get("message", {}).get("content")
    if not content:
        raise TriageError(f"Ollama returned no content: {json.dumps(body)[:500]}")
    return content.strip()
