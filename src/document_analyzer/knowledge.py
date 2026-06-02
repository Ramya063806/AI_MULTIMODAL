from __future__ import annotations

import re
from typing import Iterable

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .utils import _shorten_text



def extract_concepts(text: str, top_k: int = 40) -> list[str]:
    if not text or not text.strip():
        return []
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 3), max_features=2000)
    docs = [text]
    X = vectorizer.fit_transform(docs)
    features = vectorizer.get_feature_names_out()

    scores = [(i, float(X[0, i])) for i in range(len(features))]
    scores.sort(key=lambda x: x[1], reverse=True)
    concepts = [features[i] for i, _ in scores[:top_k]]
    concepts = [c for c in concepts if not re.fullmatch(r"[\d\W_]+", c)]
    return concepts


def build_concept_web(concepts: Iterable[str], sections: Iterable[str]) -> tuple[list[dict], list[dict]]:
    nodes = [{"id": c, "label": c} for c in concepts]
    edges = []
    concept_list = list(concepts)
    for i, a in enumerate(concept_list):
        for j in range(i + 1, len(concept_list)):
            b = concept_list[j]
            count = 0
            for s in sections:
                la = a.lower() in s.lower()
                lb = b.lower() in s.lower()
                if la and lb:
                    count += 1
            if count > 0:
                edges.append({"source": a, "target": b, "weight": count})
    return nodes, edges


def generate_socratic_questions(text: str, concepts: Iterable[str], num_questions: int = 4) -> list[dict]:
    if not text:
        return []
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    concept_list = list(concepts)
    questions = []
    templates = [
        "Explain the role of '{c}' in the document.",
        "How does '{c}' influence or connect to other ideas in this text?",
        "Why is '{c}' important for the main argument or process described?",
        "Describe how '{c}' is used in examples or applications in this document.",
    ]

    for i in range(min(num_questions, len(concept_list))):
        c = concept_list[i]
        q = templates[i % len(templates)].format(c=c)
        questions.append({"question": q, "concepts": [c]})

    if len(questions) < num_questions and len(concept_list) > 1:
        for i in range(num_questions - len(questions)):
            a = concept_list[i]
            b = concept_list[min(i + 1, len(concept_list) - 1)]
            questions.append({"question": f"How are '{a}' and '{b}' related in this document?", "concepts": [a, b]})
    return questions


def evaluate_answers(answers: list[str], questions: list[dict], text: str) -> list[dict]:
    results = []
    if not text:
        for _ in questions:
            results.append({"status": "gap", "score": 0.0, "matched": []})
        return results

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 3))
    corpus = sentences + answers
    if not corpus:
        return [{"status": "gap", "score": 0.0, "matched": []} for _ in questions]
    X = vectorizer.fit_transform(corpus)

    sent_mat = X[: len(sentences)]
    ans_mat = X[len(sentences):]

    for idx, q in enumerate(questions):
        ans_vec = ans_mat[idx] if idx < ans_mat.shape[0] else None
        if ans_vec is None or (ans_vec.nnz == 0):
            results.append({"status": "gap", "score": 0.0, "matched": []})
            continue
        sims = cosine_similarity(ans_vec, sent_mat).flatten()
        best_idx = int(sims.argmax())
        best_score = float(sims[best_idx])
        matched = []
        for si, sscore in enumerate(sims):
            if sscore >= max(0.25, best_score * 0.5):
                matched.append(sentences[si])

        if best_score >= 0.6:
            status = "understood"
        elif best_score >= 0.35:
            status = "partial"
        else:
            status = "gap"

        results.append({"status": status, "score": best_score, "matched": matched})
    return results


def generate_layered_questions(text: str, sections: list[dict], max_per_layer: int = 5) -> list[dict]:
    """Generate layered Socratic questions: recall, comprehension, analysis.

    Each question dict: {id, layer, question, hint, model_answer, section_title, page}
    """
    if not text:
        return []
    # flatten sections into list of (title, content)
    sec_list = [(s.title, s.content, s.page_number) for s in sections]
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

    concepts = extract_concepts(text, top_k=30)
    questions = []

    # Layer 1: recall (who/what/when/where) — pick sentences with named entities or dates heuristics
    recall_count = 0
    for sent in sentences:
        if recall_count >= max_per_layer:
            break
        if re.search(r"\b(\d{4}|\d{1,2}\/\d{1,2}|January|February|March|April|May|June|July|August|September|October|November|December)\b", sent, re.I):
            qtxt = f"What factual detail is stated here: '{_shorten_text(sent,80)}' ?"
            hint = sent[:200]
            questions.append({"id": f"R{recall_count+1}", "layer": "recall", "question": qtxt, "hint": hint, "model_answer": sent, "section_title": None, "page": None})
            recall_count += 1

    # Layer 2: comprehension — ask about meaning of a key concept
    comp_count = 0
    for c in concepts[: max_per_layer * 2]:
        if comp_count >= max_per_layer:
            break
        # find sentence that uses the concept
        match_sent = next((s for s in sentences if c.lower() in s.lower()), None)
        if match_sent:
            qtxt = f"Explain in your own words what '{c}' means in this document."
            hint = _shorten_text(match_sent, 200)
            questions.append({"id": f"C{comp_count+1}", "layer": "comprehension", "question": qtxt, "hint": hint, "model_answer": match_sent, "section_title": None, "page": None})
            comp_count += 1

    # Layer 3: analysis — compare/apply
    anal_count = 0
    # use pairs of top concepts
    for i in range(min(len(concepts) - 1, max_per_layer)):
        a = concepts[i]
        b = concepts[i + 1]
        qtxt = f"Analyze how '{a}' and '{b}' relate or differ in the document."
        # hint: sentences where either appears
        hint_sents = [s for s in sentences if a.lower() in s.lower() or b.lower() in s.lower()][:2]
        hint = " ".join(hint_sents)[:300]
        model = " ".join(hint_sents) if hint_sents else ""
        questions.append({"id": f"A{anal_count+1}", "layer": "analysis", "question": qtxt, "hint": hint, "model_answer": model, "section_title": None, "page": None})
        anal_count += 1

    # attach nearest section titles/pages for model answers
    for q in questions:
        # find a section that contains the model_answer
        if not q.get("model_answer"):
            continue
        for title, content, page in sec_list:
            if q["model_answer"][:30].lower() in content.lower():
                q["section_title"] = title
                q["page"] = page
                break

    return questions


def detect_prerequisites(text: str, concepts: list[str], sections: list[dict]) -> list[dict]:
    """Detect assumed prerequisite concepts using heuristics.

    Returns list of {concept, difficulty, micro_explanation, why_assumed, suggested_query}
    """
    # heuristic: concepts that appear often but lack explicit definitions nearby
    prerequisites = []
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    for c in concepts:
        # skip very short tokens
        if len(c) <= 2:
            continue
        # find definitional patterns near mentions
        pattern = re.compile(rf"\b{re.escape(c)}\b.*\b(is|are|refers to|means|defined as)\b", re.I)
        has_definition = any(pattern.search(s) for s in sentences)
        freq = sum(1 for s in sentences if c.lower() in s.lower())
        if freq >= 2 and not has_definition:
            # consider as assumed prerequisite
            difficulty = "Foundation" if freq >= 2 and len(c.split()) <= 2 else "Intermediate"
            micro = f"{c} — a term used in the document; review its basic definition to follow the text."
            why = f"The document uses '{c}' without defining it, implying prior knowledge is expected."
            query = f"what is {c} definition".strip()
            prerequisites.append({"concept": c, "difficulty": difficulty, "micro_explanation": micro, "why": why, "suggested_query": query, "occurrences": freq})

    # sort by occurrences (most critical first)
    prerequisites.sort(key=lambda x: x["occurrences"], reverse=True)
    return prerequisites

