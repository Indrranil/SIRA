def evaluate_source(url: str, text: str) -> float:
    """
    Dummy credibility evaluator.
    Returns score 0–1 based on source domain + content length.
    """
    trust = 0.5
    if any(x in url for x in ["nature", "arxiv", "springer", "research", "edu"]):
        trust += 0.3
    elif any(x in url for x in ["medium", "blog", "reddit"]):
        trust -= 0.2
    if len(text.split()) > 500:
        trust += 0.1
    return min(trust, 1.0)
