"""Provider-agnostic model client.

The pipeline's judgment steps (assort, optional LLM categorization) call ONE
function: complete(). Which provider/model runs is pure config — switch OpenAI
<-> Anthropic <-> anything else without touching stage code.

Configure via environment:
    LLM_PROVIDER = openai | anthropic        (default: openai)
    LLM_MODEL    = <model string you have access to>
                   e.g. a GPT-4-class or o-series model for openai,
                        a claude-* model for anthropic
    OPENAI_API_KEY / ANTHROPIC_API_KEY       (whichever provider you pick)
    LLM_MAX_TOKENS = 4096                     (optional)

Usage:
    from pipeline.llm import complete
    data = complete(system="You are ...", user="...", as_json=True)
"""
from __future__ import annotations
import os, json


def _cfg():
    return {
        "provider": os.environ.get("LLM_PROVIDER", "openai").lower(),
        "model": os.environ.get("LLM_MODEL", ""),
        "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", "4096")),
    }


def complete(system: str, user: str, as_json: bool = False) -> str | dict:
    """Single completion call. Returns text, or a parsed dict if as_json=True.
    The prompt is identical across providers; only the transport differs."""
    c = _cfg()
    if not c["model"]:
        raise RuntimeError("Set LLM_MODEL to the model string you want to use.")

    if c["provider"] == "openai":
        text = _openai(system, user, c, as_json)
    elif c["provider"] == "anthropic":
        text = _anthropic(system, user, c)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {c['provider']}")

    return _parse_json(text) if as_json else text


def _openai(system: str, user: str, c: dict, as_json: bool) -> str:
    from openai import OpenAI          # pip install openai ; needs OPENAI_API_KEY
    client = OpenAI()
    kwargs = dict(
        model=c["model"],
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
    )
    if as_json:
        kwargs["response_format"] = {"type": "json_object"}  # forces valid JSON
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content


def _anthropic(system: str, user: str, c: dict) -> str:
    import anthropic                   # pip install anthropic ; needs ANTHROPIC_API_KEY
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=c["model"], max_tokens=c["max_tokens"],
        system=system, messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def _parse_json(text: str) -> dict:
    """Tolerant JSON extraction (handles ```json fences / stray prose)."""
    t = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        i, j = t.find("{"), t.rfind("}")
        if i != -1 and j != -1:
            return json.loads(t[i:j + 1])
        raise
