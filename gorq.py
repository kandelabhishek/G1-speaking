import os
import time
import requests

from pathlib import Path


API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "openai/gpt-oss-20b"

session = requests.Session()
history = []

def ask(text, language):
    key_file = (
        Path.home()
        / ".config"
        / "g1-communication"
        / "groq_api_key.txt"
    )

    try:
        api_key = key_file.read_text(encoding="utf-8").strip()
    except OSError:
        return "[error] Could not read the Groq API key file"

    if not api_key:
        return "[error] The Groq API key file is empty"
  

    reply_language = (
        "Japanese" if language.lower().startswith("ja")
        else "English"
    )

    instructions = (
        "You are G1, a Unitree humanoid robot at Techshare. "
        f"Reply only in {reply_language}. "
        "Be polite, respectful, and natural. "
        "Answer the question in one or two short sentences. "
        "Do not add unrelated introductions or follow-up questions. "
        "If the question is unclear, ask the user to repeat it. "
        "If you do not know the answer, say so. "
        "Do not invent observations about your surroundings. "
        "You cannot execute robot movements. "
        "Use plain spoken text without Markdown or emojis."
        "Give the shortest useful answer, usually a few words. "
        "Use at most one short sentence. "
        "For questions about Unitree G1 specifications or capabilities, "
        "look up official information at https://www.unitree.com/g1/ "
        "or support.unitree.com before answering. "
        "Website capabilities describe the product, not actions this "
        "conversation program can perform. "
        "If a fact cannot be verified, say you do not know. "
        "You are G1 itself. Describe yourself in the first person. "
        "Say 'I am', 'I have', and 'my' instead of 'G1 is' or 'the robot has'. "
        "In Japanese, use natural first-person wording such as "
        "'私の身長は' or '〜ができます'. "
        
    )

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": instructions},
            *history,
            {"role": "user", "content": text},
        ],
        "tools": [{"type": "browser_search"}],
        "tool_choice":"auto",
        "reasoning_effort": "medium",
        "include_reasoning": False,
        "max_completion_tokens": 512,
        "temperature": 0.5,
        "stream": False,
    }

    started = time.monotonic()

    try:
        response = session.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=(10, 60),
        )

        if response.status_code == 429:
            return "[error] Groq rate limit reached. Wait before retrying."

        if not response.ok:
            return f"[error] Groq returned HTTP {response.status_code}"

        data = response.json()
        choice = data["choices"][0]

        if choice.get("finish_reason") == "length":
            return "[error] Groq reached the response token limit"

        reply = (choice["message"].get("content") or "").strip()

        if reply:
            history.extend([
                {"role": "user", "content": text},
                {"role": "assistant", "content": reply},
            ])

            # Keep the latest six question-and-answer pairs.
            history[:] = history[-12:]

        elapsed = time.monotonic() - started
        print(f"Groq reply time: {elapsed:.2f}s", flush=True)

        return reply or "[error] Groq returned no reply text"

    except requests.exceptions.RequestException:
        return "[error] Could not connect to Groq or request timed out"
    except (ValueError, KeyError, IndexError, TypeError):
        return "[error] Could not read the Groq response"