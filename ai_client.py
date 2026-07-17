import os
# pyrefly: ignore [missing-import]
from openai import OpenAI

# ── Groq API (free, extremely fast Llama inference) ───────────────────────────
# Get a free key at: https://console.groq.com

_GROQ_BASE = "https://api.groq.com/openai/v1"
_TIMEOUT   = 50  # seconds

# Fernace lite  → llama-3.1-8b-instant  (fastest, lightweight)
# Fernace Flash → llama-3.3-70b-versatile (best quality)
_MODELS_LITE = [
    "llama-3.1-8b-instant",
    "llama3-8b-8192",
    "gemma2-9b-it",
]
_MODELS_FLASH = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]

# Lazy shared client
_client = None

def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set. Add it to your .env file or Vercel environment variables.")
        _client = OpenAI(
            base_url=_GROQ_BASE,
            api_key=api_key,
            timeout=_TIMEOUT,
            max_retries=0,
        )
    return _client


def _try_models(client, model_list, messages):
    """Try each model in order, skipping rate-limited or unavailable ones."""
    for model_id in model_list:
        try:
            completion = client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=0.2,
                top_p=0.7,
                max_tokens=1024,
                stream=False
            )
            return completion.choices[0].message.content, None
        except Exception as e:
            err = str(e)
            # Skip on rate-limit (429) or model not found (404)
            if "429" in err or "404" in err or "rate" in err.lower() or "decommissioned" in err.lower():
                print(f"Skipping {model_id}: {err[:100]}")
                continue
            return None, err  # unexpected error — stop immediately
    return None, "All models are temporarily busy. Please try again in a moment."


def query_volcano_ai(prompt, history=None, model="magma2", attachment=None, deep_think=False):
    if history is None:
        history = []
    try:
        client = _get_client()
        persona = "Fernace Flash" if model == "magma-flash" else "Fernace flash lite"
        model_list = _MODELS_FLASH if model == "magma-flash" else _MODELS_LITE

        # ── Handle attachments ────────────────────────────────────────────────
        processed_prompt = prompt

        if attachment:
            file_name = attachment.get("name", "file")
            file_size = attachment.get("size", "unknown size")

            if attachment.get("type", "").startswith("image/"):
                # Groq vision (llama-3.2-11b-vision-instruct is available on Groq)
                model_list = ["llama-3.2-11b-vision-preview"] + _MODELS_LITE
                img_url     = attachment.get("data", "")
                instruction = prompt if prompt else f"Please describe this image: {file_name} in detail."
                messages_with_vision = [
                    {"role": "system", "content": f"You are Fernace ({persona}). Write math in LaTeX."},
                    *[{"role": m.get("role"), "content": m.get("content")} for m in history[-10:]],
                    {"role": "user", "content": [
                        {"type": "text", "text": instruction},
                        {"type": "image_url", "image_url": {"url": img_url}}
                    ]}
                ]
                content, err = _try_models(client, model_list, messages_with_vision)
                if err:
                    return {"success": False, "error": err}
                return {"success": True, "content": content, "reasoning": None}

            elif attachment.get("content"):
                instruction = prompt if prompt else f"Please read and describe: {file_name}."
                processed_prompt = (
                    f"[Attached Document: {file_name} ({file_size})]\n"
                    f"--- START FILE CONTENT ---\n"
                    f"{attachment['content']}\n"
                    f"--- END FILE CONTENT ---\n\n"
                    f"{instruction}"
                )
            else:
                instruction = prompt if prompt else f"Please describe this attached file: {file_name}."
                processed_prompt = f"[Attached: {file_name} ({file_size})]\n{instruction}"

        # ── Build messages ────────────────────────────────────────────────────
        system_content = (
            f"You are Fernace, an AI model (specifically, the {persona} model). "
            f"If asked your name or model, reply that you are {persona}. "
            f"Write all mathematical expressions in LaTeX ($...$ inline, $$...$$ block)."
        )
        if deep_think:
            system_content += (
                " Deep Think mode is active. Start your response with a thinking block "
                "in <thinking>...</thinking> tags, then give your final answer."
            )

        messages = [{"role": "system", "content": system_content}]
        for msg in history[-10:]:
            messages.append({"role": msg.get("role"), "content": msg.get("content")})
        messages.append({"role": "user", "content": processed_prompt})

        # ── Call Groq ─────────────────────────────────────────────────────────
        content, err = _try_models(client, model_list, messages)
        if err:
            return {"success": False, "error": err}

        reasoning = None
        if deep_think and "<thinking>" in content and "</thinking>" in content:
            parts = content.split("</thinking>", 1)
            reasoning_part = parts[0].split("<thinking>", 1)
            if len(reasoning_part) > 1:
                reasoning = reasoning_part[1].strip()
            content = parts[1].strip()

        return {"success": True, "content": content, "reasoning": reasoning}

    except Exception as e:
        return {"success": False, "error": str(e)}
