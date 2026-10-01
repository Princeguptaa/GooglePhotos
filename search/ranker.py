import re
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rapidfuzz import fuzz, process
from config import Config

def rank(query: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ranks documents based on a search query using TF-IDF and fuzzy matching.
    """
    if not documents or not query.strip():
        return []

    query = query.lower()
    
    # Extract texts and handle potential missing keys safely
    doc_texts = [doc.get('ocr_text', '').lower() for doc in documents]
    
    # 1. & 2. Build TF-IDF matrix and transform query
    vectorizer = TfidfVectorizer()
    try:
        tfidf_matrix = vectorizer.fit_transform(doc_texts)
        query_vec = vectorizer.transform([query])
    except ValueError:
        # Happens if all documents are empty or contain only stop words
        return []

    # 3. Compute cosine similarity
    cosine_sims = cosine_similarity(query_vec, tfidf_matrix).flatten()

    results = []
    
    for idx, doc in enumerate(documents):
        base_score = cosine_sims[idx]
        ocr_text = doc.get('ocr_text', '')
        
        # 4. Compute fuzzy token match
        fuzzy_boost = _fuzzy_score(query, ocr_text.lower())
        
        # 5. Final score
        final_score = (Config.TFIDF_WEIGHT * base_score) + (Config.FUZZY_WEIGHT * fuzzy_boost)
        
        # 6. Filter by threshold
        if final_score >= Config.MIN_SCORE_THRESHOLD:
            # 7. Extract snippet
            snippet_info = extract_snippet(ocr_text, query, Config.SNIPPET_MAX_LENGTH)
            
            result = {
                'id': doc.get('id'),
                'score': float(final_score),
                'snippet': snippet_info['text'],
                'highlight_ranges': snippet_info['highlight_ranges']
            }
            results.append(result)
            
    # 8. Sort descending by score
    results.sort(key=lambda x: x['score'], reverse=True)
    return results

def _fuzzy_score(query: str, doc_text: str) -> float:
    """
    Returns average fuzzy ratio across query tokens.
    """
    if not doc_text:
        return 0.0
        
    query_tokens = query.split()
    if not query_tokens:
        return 0.0
        
    doc_tokens = doc_text.split()
    if not doc_tokens:
        return 0.0
        
    total_score = 0.0
    for q_token in query_tokens:
        # Find the best match for this query token in the document tokens
        # rapidfuzz.process.extractOne returns (match, score, index)
        # score is out of 100
        best_match = process.extractOne(q_token, doc_tokens, scorer=fuzz.ratio, score_cutoff=50)
        if best_match:
            # normalize to 0-1
            total_score += (best_match[1] / 100.0)
            
    return total_score / len(query_tokens)

def extract_snippet(ocr_text: str, query: str, max_len: int = 150) -> Dict[str, Any]:
    """
    Extracts a snippet around the best match for the query and returns highlight ranges.
    """
    if not ocr_text or not query:
        return {"text": "", "highlight_ranges": []}
        
    query_tokens = query.lower().split()
    if not query_tokens:
        return {"text": ocr_text[:max_len] + "..." if len(ocr_text) > max_len else ocr_text, "highlight_ranges": []}
        
    ocr_lower = ocr_text.lower()
    
    # Find the best token to match in the text
    # We will just look for the first query token that has a good match in the text
    best_pos = -1
    best_match_len = 0
    
    # Simple strategy: find exact or partial match index for the longest query token
    longest_q_token = max(query_tokens, key=len)
    pos = ocr_lower.find(longest_q_token)
    
    if pos != -1:
        best_pos = pos
        best_match_len = len(longest_q_token)
    else:
        # If no exact substring, just find the best fuzzy match position (simplified)
        # Let's find the first word in ocr_text that strongly matches the longest query token
        doc_words = ocr_text.split()
        best_word = process.extractOne(longest_q_token, doc_words, scorer=fuzz.ratio)
        if best_word and best_word[1] > 60:
            # find index of this word in the original text
            pos = ocr_text.find(best_word[0])
            if pos != -1:
                best_pos = pos
                best_match_len = len(best_word[0])

    if best_pos == -1:
        # Fallback if no good match position found
        snippet_text = ocr_text[:max_len]
        return {"text": snippet_text + ("..." if len(ocr_text) > max_len else ""), "highlight_ranges": []}
        
    # Extract snippet around best_pos
    half_len = max_len // 2
    
    start_idx = max(0, best_pos - half_len)
    end_idx = min(len(ocr_text), best_pos + best_match_len + half_len)
    
    # Adjust to word boundaries if possible
    if start_idx > 0:
        # Try to find a space to start cleanly
        space_pos = ocr_text.find(' ', start_idx)
        if space_pos != -1 and space_pos < best_pos:
            start_idx = space_pos + 1
            
    if end_idx < len(ocr_text):
        # Try to find a space to end cleanly
        space_pos = ocr_text.rfind(' ', best_pos + best_match_len, end_idx)
        if space_pos != -1:
            end_idx = space_pos
            
    snippet = ocr_text[start_idx:end_idx]
    prefix = "..." if start_idx > 0 else ""
    suffix = "..." if end_idx < len(ocr_text) else ""
    
    final_snippet = prefix + snippet + suffix
    
    # Calculate highlight ranges relative to snippet
    # Find the matching token in the snippet
    highlight_ranges = []
    snippet_lower = final_snippet.lower()
    
    for q_token in query_tokens:
        # Search for occurrences of query tokens in the snippet
        # We use re.finditer to find boundaries if possible
        # Need to escape q_token for regex
        try:
            for match in re.finditer(re.escape(q_token), snippet_lower):
                highlight_ranges.append([match.start(), match.end()])
        except re.error:
            pass
            
    return {
        "text": final_snippet,
        "highlight_ranges": highlight_ranges
    }
