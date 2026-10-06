import re
from typing import List, Dict, Any, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rapidfuzz import fuzz, process
from config import Config

SYNONYMS = {
    # Aadhaar / UIDAI
    "aadhaar": ["aadhar", "addhar", "uidai"],
    "aadhar": ["aadhaar", "addhar", "uidai"],
    "addhar": ["aadhaar", "aadhar", "uidai"],
    "uidai": ["aadhaar", "aadhar", "addhar"],

    # Payment & Transactions
    "payment": ["paid", "transaction", "amount", "transfer", "receipt", "txn"],
    "paid": ["payment", "transaction", "amount", "transfer"],
    "transaction": ["payment", "txn", "paid", "transfer"],
    "transfer": ["payment", "transaction", "paid"],
    "txn": ["transaction", "payment", "paid"],

    # Invoice, Receipt, Bill
    "invoice": ["bill", "receipt", "total", "amount", "inv"],
    "bill": ["invoice", "receipt", "total", "amount"],
    "receipt": ["invoice", "bill", "payment", "total", "amount"],
    "price": ["invoice", "receipt", "total", "rs", "amount"],
    "item": ["invoice", "receipt", "total", "rs", "amount"],

    # Medical & Prescription
    "prescription": ["medicine", "tablet", "dr", "doctor", "patient", "mg", "pharmacy", "rx"],
    "medicine": ["prescription", "tablet", "dr", "doctor", "patient", "mg", "pharmacy"],
    "doctor": ["dr", "prescription", "clinic", "hospital"],
    "dr": ["doctor", "prescription", "clinic"],
    "patient": ["prescription", "dr", "doctor"],

    # Education & Resume
    "marksheet": ["semester", "university", "cgpa", "roll", "degree", "mark", "sheet"],
    "resume": ["skills", "experience", "education", "university", "cgpa", "cv"],
    "cv": ["skills", "experience", "education", "university", "cgpa", "resume"],
}

CONTEXT_TERMS = {
    "payment", "paid", "transaction", "transfer", "txn",
    "invoice", "bill", "receipt", "price", "total", "amount",
    "prescription", "medicine", "tablet", "pharmacy", "doctor", "dr", "patient",
    "aadhaar", "aadhar", "addhar", "uidai",
    "marksheet", "resume", "cv", "id", "card"
}

MONTHS = {
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
}

STOPWORDS = {
    "the", "a", "an", "of", "for", "in", "on", "at", "to", "from",
    "with", "by", "my", "is", "and", "or"
}

def normalize_text(text: str) -> str:
    """Normalizes text for matching by lowercasing, collapsing spaces,
    and stripping currency symbols and number formatting commas."""
    if not text:
        return ""
    text = text.lower()
    # Normalize commas within digits e.g. 6,500 -> 6500
    text = re.sub(r'(\d),(\d)', r'\1\2', text)
    # Replace common currency symbols with space
    text = re.sub(r'[₹$€£]', ' ', text)
    # Strip currency words like Rs / INR when preceding or following numbers
    text = re.sub(r'\b(?:rs|inr)\b\.?', ' ', text)
    return ' '.join(text.split())

def extract_query_clues(query: str) -> List[Dict[str, Any]]:
    """
    Decomposes a query into meaningful retrieval clues:
    - Preserves numeric values (e.g. 6500)
    - Preserves multi-word entity phrases (e.g. "Prince Gupta", "Samrat Mehta")
    - Preserves context terms (e.g. "payment", "invoice", "aadhaar", "prescription")
    - Preserves date/month terms (e.g. "September", "March")
    - Filters non-essential stopwords
    """
    if not query:
        return []

    clean_query = query.strip()
    norm_q = normalize_text(clean_query)
    raw_tokens = norm_q.split()

    if not raw_tokens:
        return []

    if len(raw_tokens) == 1:
        tok = raw_tokens[0]
        return [{
            "text": tok,
            "display": clean_query,
            "type": "numeric" if tok.isdigit() else ("context" if tok in CONTEXT_TERMS else "term"),
            "tokens": [tok]
        }]

    # Filter out stopwords only if there are meaningful tokens left
    filtered_tokens = [t for t in raw_tokens if t not in STOPWORDS or t in CONTEXT_TERMS]
    tokens = filtered_tokens if filtered_tokens else raw_tokens

    clues = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]

        # 1. Numeric token
        if tok.isdigit():
            clues.append({
                "text": tok,
                "display": tok,
                "type": "numeric",
                "tokens": [tok]
            })
            i += 1
            continue

        # 2. Month token
        if tok in MONTHS:
            clues.append({
                "text": tok,
                "display": tok.capitalize(),
                "type": "month",
                "tokens": [tok]
            })
            i += 1
            continue

        # 3. Known context term
        if tok in CONTEXT_TERMS:
            # Check for context modifier pairs like "aadhaar card", "payment receipt"
            if i + 1 < len(tokens) and tokens[i + 1] in {"card", "receipt", "bill", "slip"}:
                modifier = tokens[i + 1]
                clues.append({
                    "text": tok,
                    "display": f"{tok.capitalize()} {modifier.capitalize()}",
                    "type": "context",
                    "tokens": [tok, modifier]
                })
                i += 2
                continue
            clues.append({
                "text": tok,
                "display": tok.capitalize(),
                "type": "context",
                "tokens": [tok]
            })
            i += 1
            continue

        # 4. Consecutive non-context tokens (e.g. "Prince Gupta", "Samrat Mehta")
        entity_tokens = [tok]
        j = i + 1
        while j < len(tokens):
            next_tok = tokens[j]
            if (not next_tok.isdigit() and 
                next_tok not in CONTEXT_TERMS and 
                next_tok not in MONTHS and 
                next_tok not in STOPWORDS):
                entity_tokens.append(next_tok)
                j += 1
            else:
                break

        if len(entity_tokens) > 1:
            phrase = " ".join(entity_tokens)
            display_phrase = " ".join(t.capitalize() for t in entity_tokens)
            clues.append({
                "text": phrase,
                "display": display_phrase,
                "type": "phrase",
                "tokens": entity_tokens
            })
            i = j
        else:
            clues.append({
                "text": tok,
                "display": tok.capitalize(),
                "type": "term",
                "tokens": [tok]
            })
            i += 1

    return clues

def _score_single_clue(clue: Dict[str, Any], norm_text: str, doc_words: List[str]) -> Tuple[float, List[str], bool]:
    """
    Scores an individual clue against a document's normalized OCR text.
    Returns (score, matched_display_terms, is_literal_match).
    """
    clue_type = clue["type"]
    clue_text = clue["text"]
    display_term = clue.get("display", clue_text)

    # 1. Numeric Clue: Require exact numeric match (no fuzzy or subset match)
    if clue_type == "numeric":
        pattern = r'(?:\b|\s|^)' + re.escape(clue_text) + r'(?:\b|\s|$)'
        if re.search(pattern, norm_text):
            return 1.0, [display_term], True
        for w in doc_words:
            digits_in_w = re.findall(r'\d+', w)
            if clue_text in digits_in_w:
                return 1.0, [display_term], True
        return 0.0, [], False

    # 2. Multi-word phrase clue (e.g. "prince gupta")
    if clue_type == "phrase":
        boundary_pattern = r'(?:\b|\s|^)' + re.escape(clue_text) + r'(?:\b|\s|$)'
        if re.search(boundary_pattern, norm_text) or clue_text in norm_text:
            return 1.0, [display_term], True

        tokens = clue["tokens"]
        matched_tokens = []
        for t in tokens:
            if re.search(r'(?:\b|\s|^)' + re.escape(t) + r'(?:\b|\s|$)', norm_text) or t in doc_words:
                matched_tokens.append(t)
            elif len(t) >= 4 and any(t in w for w in doc_words if not w.isdigit()):
                matched_tokens.append(t)

        if len(matched_tokens) == len(tokens):
            return 0.88, [display_term], True
        elif len(matched_tokens) > 0:
            ratio = len(matched_tokens) / len(tokens)
            return 0.40 * ratio, [display_term], True
        return 0.0, [], False

    # 3. Context, Month, or General Term Clue
    boundary_pattern = r'(?:\b|\s|^)' + re.escape(clue_text) + r'(?:\b|\s|$)'
    if re.search(boundary_pattern, norm_text) or clue_text in doc_words:
        return 1.0, [display_term], True

    # Check synonyms
    syns = SYNONYMS.get(clue_text, [])
    for syn in syns:
        syn_pattern = r'(?:\b|\s|^)' + re.escape(syn) + r'(?:\b|\s|$)'
        if re.search(syn_pattern, norm_text) or syn in doc_words:
            # Treat exact document identity synonyms (e.g. aadhaar <-> uidai) as literal
            is_direct = (clue_text in {"aadhaar", "aadhar", "uidai"} and syn in {"aadhaar", "aadhar", "uidai"})
            return 0.95, [display_term], is_direct

    # Substring check for words with length >= 4
    if len(clue_text) >= 4 and any(clue_text in w for w in doc_words if not w.isdigit()):
        return 0.85, [display_term], True

    # RapidFuzz fallback for OCR character errors
    non_digit_words = [w for w in doc_words if not w.isdigit()]
    if non_digit_words and len(clue_text) >= 4:
        best = process.extractOne(clue_text, non_digit_words, scorer=fuzz.ratio, score_cutoff=75)
        if best:
            ratio = best[1] / 100.0
            score = 0.40 + 0.45 * ((ratio - 0.75) / 0.25)
            return round(score, 3), [display_term], True

    return 0.0, [], False

def _compute_relevance_score(clues: List[Dict[str, Any]], clue_scores: List[float], 
                             is_literal_list: List[bool],
                             norm_query: str, norm_text: str, tfidf_score: float) -> float:
    """
    Computes a combined relevance score between 0.0 and 1.0 adhering to:
    MATCHING MORE DISTINCT CLUES > MATCHING ONE CLUE
    """
    if not clues or not clue_scores or not norm_text:
        return 0.0

    k = len(clues)
    matched_clues = sum(1 for s in clue_scores if s >= 0.50)
    avg_score = sum(clue_scores) / k

    # Verbatim full query match in OCR text
    boundary_pattern = r'(?:\b|\s|^)' + re.escape(norm_query) + r'(?:\b|\s|$)'
    if re.search(boundary_pattern, norm_text):
        return min(1.0, 0.96 + (0.04 * tfidf_score))

    if norm_query in norm_text:
        return min(1.0, 0.93 + (0.04 * tfidf_score))

    # Single-clue query
    if k == 1:
        s = clue_scores[0]
        if s >= 0.95:
            return min(1.0, 0.95 + (0.05 * tfidf_score))
        elif s >= 0.80:
            return round(0.70 + 0.20 * ((s - 0.80) / 0.20) + (0.04 * tfidf_score), 3)
        elif s >= 0.50:
            return round(0.35 + 0.30 * ((s - 0.50) / 0.30), 3)
        else:
            return 0.0

    # Multi-clue query (k >= 2)
    # Case A: ALL clues matched (e.g. 2/2 clues)
    if matched_clues == k:
        final = 0.92 + (0.04 * avg_score) + (0.04 * tfidf_score)
        return min(1.0, round(final, 3))

    # Case B: Partial clue match (e.g. 1 out of 2 clues matched)
    if matched_clues > 0:
        # Require at least one matched clue to have a literal match in the document
        has_literal_match = any(is_literal_list[i] for i, s in enumerate(clue_scores) if s >= 0.50)
        if not has_literal_match:
            # Prevent hallucinated partial matches where 0 literal words of the query exist in the doc
            return 0.0

        coverage = matched_clues / k
        matched_avg = sum(s for s in clue_scores if s >= 0.50) / matched_clues
        # Documents matching only 1 clue out of 2 score in the ~0.45 - 0.58 range
        final = 0.22 + (0.46 * coverage * matched_avg) + (0.05 * tfidf_score)
        return round(final, 3)

    return 0.0

def rank(query: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ranks documents based on a search query using multi-clue decomposition.
    Search relevance is strictly based on searchable document content/OCR text,
    explicitly excluding filenames to prevent leakage.
    """
    if not documents or not query.strip():
        return []

    clean_query = query.strip().lower()
    norm_query = normalize_text(clean_query)
    clues = extract_query_clues(query)

    if not clues:
        return []

    # Strictly search OCR text, NEVER original_name or filename
    doc_ocr_texts = [doc.get('ocr_text', '') for doc in documents]
    doc_norm_texts = [normalize_text(t) for t in doc_ocr_texts]

    tfidf_scores = [0.0] * len(documents)
    try:
        non_empty = [t for t in doc_norm_texts if t]
        if non_empty:
            vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b")
            tfidf_matrix = vectorizer.fit_transform(doc_norm_texts)
            q_vec = vectorizer.transform([norm_query])
            tfidf_scores = cosine_similarity(q_vec, tfidf_matrix).flatten().tolist()
    except (ValueError, Exception):
        tfidf_scores = [0.0] * len(documents)

    results = []

    for idx, doc in enumerate(documents):
        ocr_text = doc_ocr_texts[idx]
        norm_text = doc_norm_texts[idx]

        if not norm_text:
            continue

        doc_words = [re.sub(r'[^\w]', '', w) for w in norm_text.split()]
        doc_words = [w for w in doc_words if w]

        clue_scores = []
        is_literal_list = []
        matched_terms_set = []

        for clue in clues:
            c_score, matched_for_clue, is_lit = _score_single_clue(clue, norm_text, doc_words)
            clue_scores.append(c_score)
            is_literal_list.append(is_lit)
            if c_score >= 0.50:
                for term in matched_for_clue:
                    if term not in matched_terms_set:
                        matched_terms_set.append(term)

        score = _compute_relevance_score(clues, clue_scores, is_literal_list, norm_query, norm_text, tfidf_scores[idx])

        if score >= Config.MIN_SCORE_THRESHOLD:
            matched_clues_count = sum(1 for s in clue_scores if s >= 0.50)
            snippet_info = extract_snippet(ocr_text, clean_query, Config.SNIPPET_MAX_LENGTH, matched_terms=matched_terms_set)
            
            results.append({
                'id': doc.get('id'),
                'score': float(round(score, 3)),
                'snippet': snippet_info['text'],
                'highlight_ranges': snippet_info['highlight_ranges'],
                'matched_terms': matched_terms_set if matched_terms_set else [c.get('display', c['text']) for c in clues],
                'matched_clues_count': matched_clues_count,
                'total_clues_count': len(clues)
            })

    # Sort descending by score
    results.sort(key=lambda x: x['score'], reverse=True)
    return results

def extract_snippet(ocr_text: str, query: str, max_len: int = 150, matched_terms: List[str] = None) -> Dict[str, Any]:
    """
    Extracts a snippet around the best match for the query and returns highlight ranges.
    Calculates highlight ranges relative to final snippet.
    """
    if not ocr_text or not query:
        return {"text": "", "highlight_ranges": []}

    clean_query = query.strip().lower()
    norm_query = normalize_text(clean_query)
    q_tokens = norm_query.split()

    if not q_tokens:
        snippet_text = ocr_text[:max_len]
        return {"text": snippet_text + ("..." if len(ocr_text) > max_len else ""), "highlight_ranges": []}

    ocr_lower = ocr_text.lower()

    # Determine terms to highlight
    terms_to_find = []
    if matched_terms:
        for t in matched_terms:
            t_norm = normalize_text(t)
            if t_norm and t_norm not in terms_to_find:
                terms_to_find.append(t_norm)

    if not terms_to_find:
        terms_to_find = q_tokens

    # Find best position to center snippet around
    best_pos = -1
    best_match_len = 0

    # 1. Full query verbatim
    pos = ocr_lower.find(clean_query)
    if pos != -1:
        best_pos = pos
        best_match_len = len(clean_query)
    else:
        # 2. Check matched terms in order
        for term in terms_to_find:
            pos = ocr_lower.find(term)
            if pos != -1:
                best_pos = pos
                best_match_len = len(term)
                break
            if term.isdigit():
                pattern = r'\b' + ',?'.join(term) + r'\b'
                m = re.search(pattern, ocr_lower)
                if m:
                    best_pos = m.start()
                    best_match_len = len(m.group())
                    break

        if best_pos == -1:
            # 3. Check synonyms of query tokens
            for q_tok in q_tokens:
                if q_tok in SYNONYMS:
                    for syn in SYNONYMS[q_tok]:
                        pos = ocr_lower.find(syn)
                        if pos != -1:
                            best_pos = pos
                            best_match_len = len(syn)
                            break
                if best_pos != -1:
                    break

    # If still not found, fallback to beginning
    if best_pos == -1:
        snippet_text = ocr_text[:max_len]
        final_snippet = snippet_text + ("..." if len(ocr_text) > max_len else "")
        start_idx = 0
    else:
        # Window around best_pos
        half_len = max_len // 2
        start_idx = max(0, best_pos - half_len)
        end_idx = min(len(ocr_text), best_pos + best_match_len + half_len)

        if start_idx > 0:
            space_pos = ocr_text.find(' ', start_idx)
            if space_pos != -1 and space_pos < best_pos:
                start_idx = space_pos + 1

        if end_idx < len(ocr_text):
            space_pos = ocr_text.rfind(' ', best_pos + best_match_len, end_idx)
            if space_pos != -1:
                end_idx = space_pos

        snippet = ocr_text[start_idx:end_idx]
        prefix = "..." if start_idx > 0 else ""
        suffix = "..." if end_idx < len(ocr_text) else ""
        final_snippet = prefix + snippet + suffix

    # Calculate highlight ranges relative to final_snippet
    highlight_ranges = []
    snippet_lower = final_snippet.lower()

    # Expand terms to highlight including token words and synonyms
    all_highlight_terms = set()
    for t in terms_to_find:
        all_highlight_terms.add(t)
        for sub_w in t.split():
            if len(sub_w) >= 3 and sub_w not in STOPWORDS:
                all_highlight_terms.add(sub_w)
        if t in SYNONYMS:
            for syn in SYNONYMS[t]:
                all_highlight_terms.add(syn)

    for q_tok in q_tokens:
        all_highlight_terms.add(q_tok)
        if q_tok in SYNONYMS:
            for syn in SYNONYMS[q_tok]:
                all_highlight_terms.add(syn)

    for term in sorted(all_highlight_terms, key=len, reverse=True):
        if not term:
            continue
        try:
            if term.isdigit():
                pattern = r'\b' + ',?'.join(term) + r'\b'
                for m in re.finditer(pattern, snippet_lower):
                    highlight_ranges.append([m.start(), m.end()])
            else:
                for m in re.finditer(re.escape(term), snippet_lower):
                    highlight_ranges.append([m.start(), m.end()])
        except re.error:
            pass

    return {
        "text": final_snippet,
        "highlight_ranges": highlight_ranges
    }
