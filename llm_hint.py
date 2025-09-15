import os
MODEL = os.getenv("HINT_MODEL", "gpt-4o-mini")
MAX_TOKENS = int(os.getenv("HINT_LLM_MAX_TOKENS", "60"))
ASSISTANT_NAME = os.getenv("HINT_ASSISTANT_NAME", "Word Cipher")

def rephrase_hint_or_fallback(word: str, row: int, col: int, dir_word: str, arrow: str, length: int) -> str:
    base = f"Start at row {row}, column {col}; move {dir_word} {arrow} for {length} letters."
    key = os.getenv("OPENAI_API_KEY")
    if not key or not MODEL:
        return base
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=MODEL,
            temperature=0,
            max_tokens=MAX_TOKENS,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are {ASSISTANT_NAME}, a concise word-search hint companion. "
                        "Return exactly one short sentence. No preface, no name tag, no emojis."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f'Word:{word}. Start row {row}, col {col}. '
                        f'Direction:{dir_word} ({arrow}). Length:{length}. '
                        "Reply with one sentence guiding the player to find the word."
                    ),
                },
            ],
        )
        txt = (resp.choices[0].message.content or "").strip()
        return txt[:220] or base
    except Exception:
        return base