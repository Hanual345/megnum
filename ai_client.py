import os
# pyrefly: ignore [missing-import]
from openai import OpenAI

# ── OpenRouter API key ────────────────────────────────────────────────────────
# Get a free key at: https://openrouter.ai/keys
_api_key = os.environ.get("OPENROUTER_API_KEY", "")

_OPENROUTER_BASE = "https://openrouter.ai/api/v1"
_TIMEOUT = 50  # seconds — stay under Vercel's 60s function limit

# Model fallback chains — if a model is rate-limited or unavailable, try the next
_MODELS_LITE = [
    "meta-llama/llama-3.2-3b-instruct:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "google/gemma-2-9b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2-7b-instruct:free",
]
_MODELS_FLASH = [
    "meta-llama/llama-3.1-8b-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemma-2-9b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2-7b-instruct:free",
]
_MODELS_VISION = [
    "meta-llama/llama-3.2-11b-vision-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
]

# Single shared lazy client (all models use same key/base)
_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=_OPENROUTER_BASE,
            api_key=_api_key,
            timeout=_TIMEOUT,
            max_retries=0,  # we handle retries manually via fallback models
            default_headers={
                "HTTP-Referer": "https://volcano-ai.vercel.app",
                "X-Title": "Volcano AI"
            }
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
            # Skip this model if rate-limited (429) or not available (404)
            if "429" in err or "404" in err or "rate" in err.lower() or "no endpoints" in err.lower():
                print(f"Skipping {model_id}: {err[:80]}")
                continue
            return None, err  # unexpected error — stop immediately
    return None, "All available models are temporarily busy. Please try again in 30 seconds."


def query_volcano_ai(prompt, history=None, model="magma2", attachment=None, deep_think=False):
    if history is None:
        history = []
    try:
        client = _get_client()
        persona = "Fernace Flash" if model == "magma-flash" else "Fernace flash lite"

        # ── Handle attachments ────────────────────────────────────────────────
        processed_prompt = prompt
        user_content     = None
        is_vision        = False

        if attachment:
            file_name = attachment.get("name", "file")
            file_size = attachment.get("size", "unknown size")

            if attachment.get("type", "").startswith("image/"):
                is_vision   = True
                img_url     = attachment.get("data", "")
                instruction = prompt if prompt else f"Please describe this image: {file_name} in detail."
                user_content = [
                    {"type": "text",      "text": instruction},
                    {"type": "image_url", "image_url": {"url": img_url}}
                ]
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

        if user_content:
            messages.append({"role": "user", "content": user_content})
        else:
            messages.append({"role": "user", "content": processed_prompt})

        # ── Call OpenRouter with automatic fallback ───────────────────────────
        model_list = _MODELS_VISION if is_vision else (
            _MODELS_FLASH if model == "magma-flash" else _MODELS_LITE
        )
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
        err_msg = str(e)
        if "timed out" in err_msg.lower() or "timeout" in err_msg.lower():
            err_msg = "The AI model took too long to respond. Please try again in a moment."
        return {"success": False, "error": err_msg}
