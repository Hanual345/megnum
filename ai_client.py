import os
from openai import OpenAI

# Initialize two client instances for different models using environment variables
api_key_lite = os.environ.get("NVIDIA_API_KEY_LITE", "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")
api_key_flash = os.environ.get("NVIDIA_API_KEY_FLASH", "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")

client_lite = OpenAI(
  base_url="https://integrate.api.nvidia.com/v1",
  api_key=api_key_lite
)

client_flash = OpenAI(
  base_url="https://integrate.api.nvidia.com/v1",
  api_key=api_key_flash
)

def query_volcano_ai(prompt, history=None, model='magma2', attachment=None, deep_think=False):
  if history is None:
    history = []
  try:
    # Select client and persona based on model choice
    if model == 'magma-flash':
      client = client_flash
      persona = "Fernace Flash"
    else:
      client = client_lite
      persona = "Fernace flash lite"

    # Handle attachments for text-based context inclusion
    processed_prompt = prompt
    user_content = None
    model_id = "meta/llama-3.2-3b-instruct"
    
    if attachment:
      file_name = attachment.get("name", "file")
      file_size = attachment.get("size", "unknown size")
      
      if attachment.get("type", "").startswith("image/"):
        # Use multimodal vision model for images
        model_id = "meta/llama-3.2-11b-vision-instruct"
        img_url = attachment.get("data", "")
        # Set a default instruction if prompt is empty
        instruction = prompt if prompt else f"Please describe this image: {file_name} in detail."
        user_content = [
          {"type": "text", "text": instruction},
          {"type": "image_url", "image_url": {"url": img_url}}
        ]
      elif attachment.get("content"):
        # Prepend readable file contents to the prompt context
        instruction = prompt if prompt else f"Please read, analyze, and describe the contents of this document: {file_name}."
        processed_prompt = (
          f"[Attached Document: {file_name} ({file_size})]\n"
          f"--- START FILE CONTENT ---\n"
          f"{attachment.get('content')}\n"
          f"--- END FILE CONTENT ---\n\n"
          f"{instruction}"
        )
      else:
        # Prepend description for non-readable attachments
        instruction = prompt if prompt else f"Please describe this attached file: {file_name}."
        processed_prompt = f"[Attached Attachment: {file_name} ({file_size})]\n{instruction}"

    system_content = f"You are Fernace, an AI model (specifically, the {persona} model). If the user asks what model you are, what AI you are, or your name, you must reply that you are {persona}. When writing mathematical expressions or formulas, always write them in LaTeX format using standard delimiters (e.g., $...$ for inline math and $$...$$ for block equations)."
    if deep_think:
      system_content += " Since Deep Think mode is active, you MUST start your response with a thinking block enclosed in <thinking>...</thinking> tags where you analyze the problem step-by-step. Follow it with your final response."

    # System instruction setup
    messages = [
      {"role": "system", "content": system_content}
    ]
    
    # Add last 10 messages (5 steps / turns of conversation)
    for msg in history[-10:]:
      messages.append({
        "role": msg.get("role"),
        "content": msg.get("content")
      })
      
    # Add current user prompt
    if user_content:
      messages.append({"role": "user", "content": user_content})
    else:
      messages.append({"role": "user", "content": processed_prompt})

    completion = client.chat.completions.create(
      model=model_id,
      messages=messages,
      temperature=0.2,
      top_p=0.7,
      max_tokens=1024,
      stream=False
    )
    
    content = completion.choices[0].message.content
    
    reasoning = None
    if deep_think and "<thinking>" in content and "</thinking>" in content:
        parts = content.split("</thinking>", 1)
        reasoning_part = parts[0].split("<thinking>", 1)
        if len(reasoning_part) > 1:
            reasoning = reasoning_part[1].strip()
        content = parts[1].strip()
        
    return {
      "success": True,
      "content": content,
      "reasoning": reasoning
    }
  except Exception as e:
    return {
      "success": False,
      "error": str(e)
    }
