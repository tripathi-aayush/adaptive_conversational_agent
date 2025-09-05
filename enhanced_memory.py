from collections import defaultdict

class EnhancedKeywordMemory:
    def __init__(self):
        self.keywords = []
        self.asked_keywords = set()
        self.concept_keywords = defaultdict(set)  # concept -> set of related keywords
        self.keyword_concepts = {}  # keyword -> concept
        self.current_concept = None
        
    def add_keywords(self, new_keywords, concept=None):
        """Add keywords and optionally associate them with a concept"""
        for word in new_keywords:
            word_lower = word.lower()
            if word_lower not in self.asked_keywords:
                self.keywords.append(word_lower)
                
            if concept:
                self.concept_keywords[concept].add(word_lower)
                self.keyword_concepts[word_lower] = concept
    
    def get_unused_keyword(self, prefer_concept=None):
        """Get an unused keyword, preferring those from a specific concept"""
        if prefer_concept and prefer_concept in self.concept_keywords:
            for keyword in self.concept_keywords[prefer_concept]:
                if keyword not in self.asked_keywords:
                    self.asked_keywords.add(keyword)
                    return keyword
        
        # Fallback to any unused keyword
        for keyword in self.keywords:
            if keyword not in self.asked_keywords:
                self.asked_keywords.add(keyword)
                return keyword
        return None
    
    def get_concept_keywords(self, concept):
        """Get all keywords associated with a concept"""
        return list(self.concept_keywords.get(concept, []))
    
    def identify_concept_from_text(self, text):
        """Try to identify the main concept from text based on keywords"""
        text_lower = text.lower()
        concept_scores = defaultdict(int)
        
        for word in text_lower.split():
            if word in self.keyword_concepts:
                concept = self.keyword_concepts[word]
                concept_scores[concept] += 1
        
        if concept_scores:
            return max(concept_scores.items(), key=lambda x: x[1])[0]
        return None
    
    def set_current_concept(self, concept):
        """Set the current concept being discussed"""
        self.current_concept = concept
    
    def get_current_concept(self):
        """Get the current concept being discussed"""
        return self.current_concept
