import re
from dataclasses import dataclass
from typing import List, Dict, Tuple, Set

# Lazy spaCy load (so app boots even if model missing)
_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        try:
            import spacy

            _nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            # As a fallback, try to load via package name if linked differently
            import spacy

            try:
                _nlp = spacy.load("en_core_web_sm")
            except Exception:
                raise RuntimeError(
                    "spaCy model 'en_core_web_sm' not found. "
                    "Run: python -m spacy download en_core_web_sm"
                )
    return _nlp


# Entity labels we’ll keep
ENTITY_LABELS = {
    "PERSON",
    "ORG",
    "GPE",
    "LOC",
    "PRODUCT",
    "EVENT",
    "WORK_OF_ART",
    "FAC",
    "NORP",
}


@dataclass(frozen=True)
class Node:
    id: str  # normalized text
    label: str  # original text
    type: str  # spaCy label


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    relation: str


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def _extract_entities(doc) -> List[Node]:
    nodes: Dict[str, Node] = {}
    for ent in doc.ents:
        if ent.label_ in ENTITY_LABELS:
            nid = _normalize(ent.text)
            if nid not in nodes:
                nodes[nid] = Node(id=nid, label=ent.text.strip(), type=ent.label_)
    return list(nodes.values())


def _relation_from_span(span_text: str) -> str:
    """Very light relation guess from connecting text."""
    # prioritize short verbs/preps/nouns as relation labels
    text = span_text.strip().lower()
    text = re.sub(r"[^a-z0-9\s\-_/]", "", text)
    text = re.sub(r"\s+", " ", text)
    # common fillers -> reduce
    text = re.sub(
        r"\b(the|a|an|of|and|to|in|for|with|on|as|by|from)\b", "", text
    ).strip()
    if not text:
        return "related_to"
    # truncate to keep relations short
    return text[:40]


def _extract_sentence_edges(doc) -> List[Edge]:
    edges: List[Edge] = []
    for sent in doc.sents:
        ents = [e for e in sent.ents if e.label_ in ENTITY_LABELS]
        if len(ents) < 2:
            continue
        # pairwise within sentence; relation is the text between them
        ents_sorted = sorted(ents, key=lambda e: e.start_char)
        for i in range(len(ents_sorted) - 1):
            a, b = ents_sorted[i], ents_sorted[i + 1]
            between = sent.text[
                a.end_char - sent.start_char : b.start_char - sent.start_char
            ]
            rel = _relation_from_span(between)
            src = _normalize(a.text)
            tgt = _normalize(b.text)
            if src != tgt:
                edges.append(Edge(source=src, target=tgt, relation=rel))
    return edges


def _cooccurrence_edges(nodes: List[Node]) -> List[Edge]:
    """Fallback: simple co-occurrence edges (undirected as two directed)."""
    out: List[Edge] = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            out.append(
                Edge(source=nodes[i].id, target=nodes[j].id, relation="co_occurs")
            )
    return out


def dedup_edges(edges: List[Edge]) -> List[Edge]:
    seen: Set[Tuple[str, str, str]] = set()
    out: List[Edge] = []
    for e in edges:
        key = (e.source, e.target, e.relation)
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out


def extract_triplets_from_texts(texts: List[str]) -> Dict:
    """
    Input: list of doc strings (e.g., summaries).
    Output: { nodes: [{id,label,type}], edges: [{source,target,relation}] }
    """
    nlp = _get_nlp()
    node_map: Dict[str, Node] = {}
    all_edges: List[Edge] = []

    for t in texts:
        if not t or not t.strip():
            continue
        doc = nlp(t)
        nodes = _extract_entities(doc)
        for n in nodes:
            if n.id not in node_map:
                node_map[n.id] = n

        edges = _extract_sentence_edges(doc)
        if not edges and len(nodes) >= 2:
            # fallback to co-occurrence if no explicit relation discovered
            edges = _cooccurrence_edges(nodes)

        all_edges.extend(edges)

    final_nodes = list(node_map.values())
    final_edges = dedup_edges(all_edges)

    # Cytoscape-friendly structure
    return {
        "nodes": [
            {"data": {"id": n.id, "label": n.label, "type": n.type}}
            for n in final_nodes
        ],
        "edges": [
            {"data": {"source": e.source, "target": e.target, "label": e.relation}}
            for e in final_edges
        ],
        "counts": {"nodes": len(final_nodes), "edges": len(final_edges)},
    }
