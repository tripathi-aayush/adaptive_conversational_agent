class LadderTracker:
    def __init__(self):
        self.current_subtopic = None
        self.current_level = 0  # 0 = main question, 1-3 = ladder down levels
        self.max_levels = 3
        self.original_question = None
        self.ladder_questions = []
        self.recovery_mode = False
        self.subtopic_attempts = {}
        self.recovery_questions_remaining = 0
        self.recovery_questions_total = 0
        
    def start_new_subtopic(self, subtopic):
        """Start a new subtopic with main question"""
        self.current_subtopic = subtopic
        self.current_level = 0
        self.original_question = None
        self.ladder_questions = []
        self.recovery_mode = False
        self.recovery_questions_remaining = 0
        self.recovery_questions_total = 0
        
    def go_up_ladder(self):
        """Move up one level in the ladder."""
        if self.current_level > 0:
            self.current_level -= 1
            return True
        return False
    
    def go_down_ladder(self):
        """Move down one level in the ladder"""
        if self.current_level < self.max_levels:
            self.current_level += 1
            return True
        return False
    
    def start_recovery(self, questions: int = 3):
        """Start recovery mode to build back up with a fixed number of off-topic questions."""
        self.recovery_mode = True
        self.recovery_questions_total = max(0, int(questions))
        self.recovery_questions_remaining = self.recovery_questions_total

    def consume_recovery_question(self):
        """Consume one off-topic question from the recovery counter."""
        if self.recovery_questions_remaining > 0:
            self.recovery_questions_remaining -= 1

    def end_recovery(self):
        """Exit recovery mode."""
        self.recovery_mode = False
        self.recovery_questions_remaining = 0
        self.recovery_questions_total = 0
    
    def reset_for_new_subtopic(self):
        """Reset tracker for new subtopic"""
        if self.current_subtopic:
            if self.current_subtopic not in self.subtopic_attempts:
                self.subtopic_attempts[self.current_subtopic] = 0
            self.subtopic_attempts[self.current_subtopic] += 1
        
        self.current_subtopic = None
        self.current_level = 0
        self.original_question = None
        self.ladder_questions = []
        self.recovery_mode = False
        self.recovery_questions_remaining = 0
        self.recovery_questions_total = 0
    
    def get_status(self):
        """Get current ladder status"""
        return {
            'subtopic': self.current_subtopic,
            'level': self.current_level,
            'recovery_mode': self.recovery_mode,
            'recovery_remaining': self.recovery_questions_remaining,
            'can_go_deeper': self.current_level < self.max_levels,
            'should_switch': self.should_switch_subtopic()
        }

    def should_switch_subtopic(self):
        """Check if we should switch to a new subtopic"""
        return self.current_level >= self.max_levels and not self.recovery_mode

    def assign_subtopic(self, subtopic: str, reset: bool = False):
        """
        Assign the current subtopic.
        - When reset=True, this behaves like starting a new subtopic (resets level to L0).
        - When reset=False, only set subtopic if empty and DO NOT change current_level.
        """
        if not subtopic:
            return
        if reset:
            self.start_new_subtopic(subtopic)
        else:
            if not self.current_subtopic:
                self.current_subtopic = subtopic
