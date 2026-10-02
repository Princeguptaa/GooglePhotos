import re
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rapidfuzz import fuzz, process
from config import Config

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
    return ' '.join(text.split())

def rank(query: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ranks documents based on a search query.
    Exact substring matches score 90%+.
    Partial/incidental overlap scores lower or is filtered below MIN_SCORE_THRESHOLD.
    """
    if not documents or not query.strip():
        return []

    clean_query = query.strip().lower()
    norm_query = normalize_text(clean_query)
    q_tokens = norm_query.split()
    
    if not q_tokens:
        return []

    # Optional TF-IDF for corpus-level term specificity
    doc_raw_texts = [doc.get('ocr_text', '').lower() for doc in documents]
    doc_norm_texts = [normalize_text(t) for t in doc_raw_texts]

    tfidf_scores = [0.0] * len(documents)
    try:
        vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b")
        tfidf_matrix = vectorizer.fit_transform(doc_norm_texts)
        q_vec = vectorizer.transform([norm_query])
        tfidf_scores = cosine_similarity(q_vec, tfidf_matrix).flatten().tolist()
    except (ValueError, Exception):
        tfidf_scores = [0.0] * len(documents)

    results = []

    for idx, doc in enumerate(documents):
        ocr_text = doc.get('ocr_text', '')
        raw_text = doc_raw_texts[idx]
        norm_text = doc_norm_texts[idx]

        score = _compute_match_score(clean_query, norm_query, q_tokens, raw_text, norm_text, tfidf_scores[idx])

        if score >= Config.MIN_SCORE_THRESHOLD:
            snippet_info = extract_snippet(ocr_text, clean_query, Config.SNIPPET_MAX_LENGTH)
            results.append({
                'id': doc.get('id'),
                'score': float(round(score, 3)),
                'snippet': snippet_info['text'],
                'highlight_ranges': snippet_info['highlight_ranges']
            })

    # Sort descending by score
    results.sort(key=lambda x: x['score'], reverse=True)
    return results

def _compute_match_score(clean_query: str, norm_query: str, q_tokens: List[str], 
                         raw_text: str, norm_text: str, tfidf_score: float) -> float:
    """Computes a high-fidelity relevance score between 0.0 and 1.0."""
    if not norm_text:
        return 0.0

    # 1. Exact full query verbatim in raw or normalized text
    # Check word boundary first
    boundary_pattern = r'(?:\b|\s|^)' + re.escape(norm_query) + r'(?:\b|\s|$)'
    if re.search(boundary_pattern, norm_text) or re.search(r'(?:\b|\s|^)' + re.escape(clean_query) + r'(?:\b|\s|$)', raw_text):
        return min(1.0, 0.96 + (0.04 * tfidf_score))

    # Exact substring (even inside a longer word/token)
    if norm_query in norm_text or clean_query in raw_text:
        return min(1.0, 0.91 + (0.04 * tfidf_score))

    # Clean words in doc for token matching
    doc_words = [re.sub(r'[^\w]', '', w) for w in norm_text.split()]
    doc_words = [w for w in doc_words if w]
    if not doc_words:
        return 0.0

    token_scores = []
    for q_tok in q_tokens:
        tok_score = 0.0
        if q_tok.isdigit():
            # For pure digit query: require exact numeric match
            for w in doc_words:
                digits_in_w = re.findall(r'\d+', w)
                if q_tok in digits_in_w:
                    tok_score = 1.0
                    break
            if tok_score == 0.0 and re.search(r'\b' + re.escape(q_tok) + r'\b', norm_text):
                tok_score = 1.0
            # If not exact match, do NOT match differing numbers (prevents 1500 matching 6500)
        else:
            # Word token
            if q_tok in doc_words or re.search(r'\b' + re.escape(q_tok) + r'\b', norm_text):
                tok_score = 1.0
            else:
                # Substring check for words
                if len(q_tok) >= 3 and any(q_tok in w for w in doc_words if not w.isdigit()):
                    tok_score = 0.85
                else:
                    # Fuzzy match against non-digit words
                    non_digit_words = [w for w in doc_words if not w.isdigit()]
                    if non_digit_words:
                        best = process.extractOne(q_tok, non_digit_words, scorer=fuzz.ratio, score_cutoff=70)
                        if best:
                            ratio = best[1] / 100.0
                            tok_score = 0.35 + 0.50 * ((ratio - 0.70) / 0.30)

        token_scores.append(tok_score)

    if not token_scores:
        return 0.0

    # Single-token query
    if len(q_tokens) == 1:
        s = token_scores[0]
        if s >= 0.95:
            return min(1.0, 0.95 + (0.05 * tfidf_score))
        elif s >= 0.80:
            return round(0.70 + 0.20 * ((s - 0.80) / 0.20), 3)
        elif s >= 0.50:
            return round(0.20 + 0.45 * ((s - 0.50) / 0.30), 3)
        else:
            return 0.0

    # Multi-token query
    exact_count = sum(1 for s in token_scores if s >= 0.95)
    matched_count = sum(1 for s in token_scores if s >= 0.50)
    
    if exact_count == len(q_tokens):
        # All tokens matched exactly
        if norm_query in norm_text:
            return min(1.0, 0.98)
        return min(1.0, 0.93 + (0.04 * tfidf_score))
    elif matched_count > 0:
        # Partial match
        avg_score = sum(token_scores) / len(token_scores)
        coverage = matched_count / len(q_tokens)
        final = avg_score * (coverage ** 0.5) * 0.75 + (0.05 * tfidf_score)
        return round(final, 3)
    else:
        return 0.0

def extract_snippet(ocr_text: str, query: str, max_len: int = 150) -> Dict[str, Any]:
    """
    Extracts a snippet around the best match for the query and returns highlight ranges.
    Supports comma-formatted digits (e.g. 6,500 for query 6500) and currency symbols.
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
    
    # Find match position
    best_pos = -1
    best_match_len = 0
    
    # 1. Try finding full query
    pos = ocr_lower.find(clean_query)
    if pos != -1:
        best_pos = pos
        best_match_len = len(clean_query)
    else:
        # Check digit queries with optional commas
        longest_tok = max(q_tokens, key=len)
        if longest_tok.isdigit():
            pattern = r'\b' + ',?'.join(longest_tok) + r'\b'
            m = re.search(pattern, ocr_lower)
            if m:
                best_pos = m.start()
                best_match_len = len(m.group())
        
        if best_pos == -1:
            pos = ocr_lower.find(longest_tok)
            if pos != -1:
                best_pos = pos
                best_match_len = len(longest_tok)
            else:
                doc_words = ocr_text.split()
                best_word = process.extractOne(longest_tok, doc_words, scorer=fuzz.ratio)
                if best_word and best_word[1] > 60:
                    pos = ocr_text.find(best_word[0])
                    if pos != -1:
                        best_pos = pos
                        best_match_len = len(best_word[0])

    if best_pos == -1:
        snippet_text = ocr_text[:max_len]
        return {"text": snippet_text + ("..." if len(ocr_text) > max_len else ""), "highlight_ranges": []}

    # Extract snippet window around best_pos
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

    for q_tok in q_tokens:
        try:
            if q_tok.isdigit():
                pattern = r'\b' + ',?'.join(q_tok) + r'\b'
                for m in re.finditer(pattern, snippet_lower):
                    highlight_ranges.append([m.start(), m.end()])
            else:
                for m in re.finditer(re.escape(q_tok), snippet_lower):
                    highlight_ranges.append([m.start(), m.end()])
        except re.error:
            pass

    return {
        "text": final_snippet,
        "highlight_ranges": highlight_ranges
    }

