class LadderTracker:
    def __init__(self):
        self.current_subtopic = None
        self.current_level = 0  # L0 is the baseline
        self.min_level = -3     # Easiest remedial level
        self.max_level = 3      # Hardest challenge level
        
    def go_up_ladder(self):
        """Move up one level in the ladder, maxing out at L+3."""
        if self.current_level < self.max_level:
            self.current_level += 1
            return True
        return False
    
    def go_down_ladder(self):
        """Move down one level in the ladder, bottoming out at L-3."""
        if self.current_level > self.min_level:
            self.current_level -= 1
            return True
        return False
    
    def reset_for_new_subtopic(self):
        """Reset tracker for a new subtopic, starting at L0."""
        self.current_subtopic = None
        self.current_level = 0
    
    def get_status(self):
        """Get current ladder status."""
        return {
            'subtopic': self.current_subtopic,
            'level': self.current_level,
        }

    def assign_subtopic(self, subtopic: str, reset: bool = False):
        """
        Assign the current subtopic.
        If reset=True, this starts a new subtopic journey from L0.
        """
        if reset:
            self.reset_for_new_subtopic()
        
        if not self.current_subtopic:
            self.current_subtopic = subtopic