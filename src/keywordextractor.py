import spacy

nlp = spacy.load("en_core_web_md")

GENERIC_WORDS = {
    "ai", "ml", "data", "model", "models", "algorithm", "algorithms", "learning",
    "approach", "method", "task", "system", "input", "output", "feature", "features",
    "information", "process", "technique", "result", "analysis", "type", "problem"
}

def extract_keywords(text):
    doc = nlp(text)
    keywords = set()

    for chunk in doc.noun_chunks:
        candidate = chunk.text.strip().lower()
        if not chunk.root.is_stop and len(candidate) > 1:
            if all(word not in GENERIC_WORDS for word in candidate.split()):
                keywords.add(candidate)

    
    for token in doc:
        word = token.text.strip().lower()
        if token.pos_ in ["NOUN", "PROPN"] and not token.is_stop:
            if word not in GENERIC_WORDS and len(word) > 2:
                keywords.add(word)

    return list(set(keywords))
