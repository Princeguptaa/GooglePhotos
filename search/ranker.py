import re
from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config import Config

def rank(query: str, documents: list[dict]) -> list[dict]:
    if not documents or not query.strip():
        return []

    doc_texts = [doc.get('ocr_text', '') for doc in documents]
    
    # 1. TF-IDF
    vectorizer = TfidfVectorizer(stop_words='english', lowercase=True)
    try:
        tfidf_matrix = vectorizer.fit_transform(doc_texts)
        query_vec = vectorizer.transform([query])
        cosine_sims = cosine_similarity(query_vec, tfidf_matrix).flatten()
    except ValueError:
        # Happens if vocab is empty (all texts are empty or stop words)
        cosine_sims = [0.0] * len(documents)

    query_tokens = [t.lower() for t in query.split() if t.strip()]

    scored_docs = []
    for i, doc in enumerate(documents):
        base_score = cosine_sims[i]
        
        # 2. Fuzzy Match
        doc_text = doc.get('ocr_text', '')
        doc_text_lower = doc_text.lower()
        
        if not doc_text_lower or not query_tokens:
            fuzzy_boost = 0.0
        else:
            fuzzy_scores = []
            for token in query_tokens:
                score = fuzz.partial_ratio(token, doc_text_lower) / 100.0
                fuzzy_scores.append(score)
            fuzzy_boost = sum(fuzzy_scores) / len(fuzzy_scores)
            
        final_score = (Config.TFIDF_WEIGHT * base_score) + (Config.FUZZY_WEIGHT * fuzzy_boost)
        
        if final_score >= Config.MIN_SCORE_THRESHOLD:
            snippet_data = extract_snippet(doc_text, query, Config.SNIPPET_MAX_LENGTH)
            scored_docs.append({
                'image_id': doc['id'],
                'thumbnail_url': f"/api/images/{doc['id']}",
                'original_name': doc['original_name'],
                'score': round(final_score * 100),
                'snippet': snippet_data['text'],
                'highlight_ranges': snippet_data['highlight_ranges']
            })
            
    scored_docs.sort(key=lambda x: x['score'], reverse=True)
    return scored_docs


def extract_snippet(ocr_text: str, query: str, max_len: int = 150) -> dict:
    if not ocr_text:
        return {"text": "", "highlight_ranges": []}

    query_tokens = [t.lower() for t in query.split() if t.strip()]
    text_lower = ocr_text.lower()
    
    best_pos = -1
    best_token = ""
    for token in query_tokens:
        idx = text_lower.find(token)
        if idx != -1:
            best_pos = idx
            best_token = token
            break
            
    if best_pos == -1:
        # Fallback to fuzzy find roughly
        best_pos = 0

    half_len = max_len // 2
    start = max(0, best_pos - half_len)
    end = min(len(ocr_text), best_pos + half_len)
    
    snippet = ocr_text[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(ocr_text):
        snippet = snippet + "..."
        
    # Highlighting (very basic naive approach for MVP)
    highlight_ranges = []
    snippet_lower = snippet.lower()
    for token in query_tokens:
        # find all occurrences of token in snippet
        for match in re.finditer(re.escape(token), snippet_lower):
            highlight_ranges.append([match.start(), match.end()])

    return {
        "text": snippet,
        "highlight_ranges": highlight_ranges
    }
