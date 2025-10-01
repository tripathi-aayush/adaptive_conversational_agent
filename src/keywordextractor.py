from keybert import KeyBERT # type: ignore

# Initialize the KeyBERT model. 
# This will be done only once when the module is first imported.
kw_model = KeyBERT()

def extract_keywords(text):
    """
    Extracts the most relevant technical keywords from a given text using KeyBERT.
    """
    try:
        # We use the model to extract keywords.
        # keyphrase_ngram_range: Looks for single words up to 3-word phrases.
        # stop_words='english': Removes common English words.
        # use_mmr=True, diversity=0.7: This is important! It ensures the keywords
        # are diverse and not just variations of the same concept.
        # top_n=3: Extracts a maximum of 3 keywords, as requested.
        keywords = kw_model.extract_keywords(text, 
                                             keyphrase_ngram_range=(1, 3), 
                                             stop_words='english', 
                                             use_mmr=True, 
                                             diversity=0.7,
                                             top_n=3)
        
        # The model returns keywords with a relevance score. We only need the words.
        # We also filter out any keywords with very low relevance (score < 0.3).
        # This helps to further filter out generic or irrelevant words.
        
        # keywords look like [('machine learning', 0.56), ('supervised learning', 0.45)]
        
        keyword_list = [kw for kw, score in keywords if score > 0.3]
        
        return keyword_list
        
    except Exception as e:
        print(f"KeyBERT error: {e}")
        return []