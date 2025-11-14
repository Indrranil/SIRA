import os, httpx
from config import settings
from transformers import pipeline


async def summarize_text(text: str, max_tokens: int = 256) -> str:
    """
    Summarize via local Ollama (LLaMA) if available;
    fallback: naive first-few-sentences summary.
    """
    prompt = (
        f"Summarize concisely in 5 bullet points.\n\nTEXT:\n{text[:4000]}\n\nBullets:"
    )
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{os.getenv('OLLAMA_HOST', 'http://localhost:11434')}/api/generate",
                json={"model": os.getenv("LLAMA_MODEL", "llama3.1"), "prompt": prompt},
            )
            if r.status_code == 200:
                data = r.json()
                return data.get("response", "").strip() or text[:500]
    except Exception:
        pass
    # Fallback: take first 3–5 sentences
    sents = text.split(". ")
    return "- " + "\n- ".join(sents[:5])[:800]


def get_summarizer():
    return pipeline("summarization", model="facebook/bart-large-cnn")


summarizer = get_summarizer()


def summarize_text(text: str, max_length: int = 150) -> str:
    summary = summarizer(text, max_length=max_length, min_length=40, do_sample=False)
    return summary[0]["summary_text"].strip()
