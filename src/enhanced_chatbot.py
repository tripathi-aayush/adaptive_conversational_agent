from keywordextractor import extract_keywords
from enhanced_memory import EnhancedKeywordMemory
from ladder_tracker import LadderTracker
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load .env file
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("No API key found.")

genai.configure(api_key=api_key)

class EnhancedChatbot:
    def __init__(self):
        self.memory = EnhancedKeywordMemory()
        self.ladder_tracker = LadderTracker()
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.conversation_count = 0
        self.current_concept = None
        self.user_learning_area = None
        self.session_started = False
        self.climbing_up = False
        self.last_correct_answer = ""
        self.original_l0_question = ""
        self.must_answer_l0 = False
        self.in_recovery_mode = False  # Track that we entered recovery due to climb-fail (for clarity, logic driven by tracker)
        self._last_feedback_type = None
        
    def get_next_question(self, chat_history, last_score=None, last_concept=None):
        """Get the next question using precise ladder approach"""
        self.conversation_count += 1
        
        if not self.session_started and chat_history:
            self._extract_user_learning_area(chat_history)
            self.session_started = True
        
        if (hasattr(self, '_last_feedback_type') and 
            self._last_feedback_type == "clarification_request"):
            return self._rephrase_current_question(chat_history)
        
        question_text = self._generate_contextual_question(
            chat_history, 
            last_score, 
            last_concept
        )
        
        return {
            "role": "assistant",
            "content": question_text
        }
    
    def _rephrase_current_question(self, chat_history):
        """Rephrase the current question more clearly without changing ladder level"""
        # Get the last assistant question
        last_question = ""
        for message in reversed(chat_history):
            if message["role"] == "assistant":
                last_question = message["content"]
                break
        
        current_status = self.ladder_tracker.get_status()
        level = current_status.get('level', 0)
        subtopic = current_status.get('subtopic', 'the concept')
        
        prompt = f"""The learner asked for clarification on this question: "{last_question}"
        
Rephrase the same question more clearly while keeping the same meaning and difficulty level (L{level}):
- Use simpler words if possible
- Break down complex terms
- Make the question structure clearer
- Keep the same core concept being tested
- Stay at the same difficulty level
- Be encouraging: "Let me rephrase that..." or "In other words..."

Provide just the rephrased question."""
        
        try:
            response = self.model.generate_content(prompt)
            question = response.text.strip()
            
            # Clean up the response
            if "Question:" in question:
                question = question.split("Question:")[-1].strip()
            
            # Add level prefix (same level as before)
            level_label = f"L{level}"
            upper = question.lstrip().upper()
            already_labeled = any(upper.startswith(f"{lab}:") for lab in ["L0", "L1", "L2", "L3"])
            if not already_labeled:
                question = f"{level_label}: {question}"
            
            return {
                "role": "assistant", 
                "content": question
            }
            
        except Exception:
            # Fallback rephrasing
            fallback = f"Let me rephrase: {last_question}"
            level_label = f"L{level}"
            return {
                "role": "assistant",
                "content": f"{level_label}: {fallback}"
            }
    
    def _generate_contextual_question(self, chat_history, last_score=None, last_concept=None):
        """Generate contextual question based on precise ladder flow"""
        ladder_status = self.ladder_tracker.get_status()
        
        if last_score is not None:
            if last_score > 60:  # Correct answer
                if ladder_status['level'] == 0:  # At L0
                    if self.must_answer_l0:
                        # L0 answered correctly after climbing up - now switch subtopic
                        self.ladder_tracker.reset_for_new_subtopic()
                        self.climbing_up = False
                        self.must_answer_l0 = False
                        self.original_l0_question = ""
                    else:
                        # First L0 correct - move to new subtopic
                        self.ladder_tracker.reset_for_new_subtopic()
                        self.climbing_up = False
                else:  # At L1-L3, start mandatory climb up
                    self.climbing_up = True
                    self.must_answer_l0 = True
                    # Use the user's last answer as the "correct" basis
                    self.last_correct_answer = chat_history[-1]['content'] if chat_history else ""
                    self.ladder_tracker.go_up_ladder()
            elif last_score <= 60:  # Incorrect/incomplete answer
                if self.climbing_up:
                    # Exit ladder flow and start 3-question off-topic recovery to regain confidence
                    self.ladder_tracker.start_recovery(questions=3)
                    self.climbing_up = False
                    self.must_answer_l0 = False
                elif not self.climbing_up and ladder_status['can_go_deeper']:
                    if (hasattr(self, '_last_feedback_type') and 
                        self._last_feedback_type == "zero_knowledge"):
                        # Don't descend ladder - immediately switch to new subtopic
                        self.ladder_tracker.reset_for_new_subtopic()
                        self.climbing_up = False
                        self.must_answer_l0 = False
                        self.original_l0_question = ""
                    else:
                        # Normal descent for partial attempts
                        # Store original L0 question when starting descent
                        if ladder_status['level'] == 0:
                            # previous assistant question (L0)
                            self.original_l0_question = chat_history[-2]['content'] if len(chat_history) >= 2 else ""

                        self.ladder_tracker.go_down_ladder()

                        prev_assistant_q = chat_history[-2]['content'] if len(chat_history) >= 2 else ""
                        derived_from_q = None
                        try:
                            if prev_assistant_q:
                                derived_from_q = self.memory.identify_concept_from_text(prev_assistant_q)
                        except Exception:
                            derived_from_q = None
                        # Build a robust fallback subtopic
                        candidate_subtopic = last_concept or derived_from_q or self.current_concept or self.user_learning_area
                        self.ladder_tracker.assign_subtopic(candidate_subtopic, reset=False)
                elif ladder_status['level'] >= 3:  # Max depth reached - fail case
                    # Encourage briefly then switch subtopic
                    self.ladder_tracker.reset_for_new_subtopic()
                    self.climbing_up = False
                    self.must_answer_l0 = False
                    self.original_l0_question = ""
        
        recovery_status = self.ladder_tracker.get_status()
        if recovery_status['recovery_mode']:
            remaining = recovery_status.get('recovery_remaining', 0)
            if remaining > 0:
                # Compose a confidence-boosting, non-technical question about hobbies/interests
                # Do NOT apply ladder logic in these questions.
                prompt = f"""You are helping a learner regain confidence. Ask a light, encouraging, non-technical question about their hobbies or interests.
Guidelines:
- No technical content.
- Friendly and conversational.
- Ask just One short supportive question.
- Make it sound natural.

Ask just one question. Be chill."""
                try:
                    response = self.model.generate_content(prompt + f"\n\nRecent conversation: {chat_history[-2:] if chat_history else 'None'}")
                    question = response.text.strip()
                except Exception:
                    question = "What do you enjoy doing in your free time?"
                
                # Consume one recovery question and return immediately
                self.ladder_tracker.consume_recovery_question()
                return question
            else:
                # Recovery completed: end recovery and transition to a new subtopic within the user's initial topic
                self.ladder_tracker.end_recovery()
                # Clear climb flags and prepare for a fresh subtopic
                self.climbing_up = False
                self.must_answer_l0 = False
                self.original_l0_question = ""
                # Ensure we reset ladder state so next question is a fresh L0 for a new subtopic
                self.ladder_tracker.reset_for_new_subtopic()
                # Fall through to normal L0-new-subtopic generation below
        
        # Generate question based on current ladder state
        current_status = self.ladder_tracker.get_status()
        learning_context = f"focusing on {self.user_learning_area}" if self.user_learning_area else "general technical concepts"
        
        if current_status['level'] == 0:
            if self.climbing_up or self.must_answer_l0:
                prompt = f"""The learner has understood the components through the ladder. Now they must answer the original L0 question.
                
Using their understanding from: "{self.last_correct_answer}"
                
Reframe the original L0 question about {current_status.get('subtopic', last_concept)}:
- Use simpler terms they've shown they understand
- Connect back to their correct answer
- Be encouraging: "Great! Now putting that together..." or "Perfect! With that understanding..."
- Make it clear this is the main concept they need to grasp
- Related to {self.user_learning_area if self.user_learning_area else 'their learning area'}

Ask just the restated L0 question."""
            else:
                prompt = f"""You are an expert technical interviewer. The user's field is "{learning_context}".

Your task is to ask a single, concise, and professional conceptual L0 question about a NEW subtopic from the user's field.

**RULES:**
1.  The question must be short and to the point (under 25 words).
2.  Avoid long, conversational introductions. A brief greeting is okay.
3.  The question must be about a core concept related to  "{self.user_learning_area if self.user_learning_area else 'their learning area'}"
**Example of a good question:**
"Great, let's start with a core concept. What is the primary purpose of an activation function in a neural network?"
Ask just the question, be direct and professional."""
        
        elif current_status['level'] == 1:
            if self.climbing_up:
                prompt = f"""Great! The learner answered correctly at L2: "{self.last_correct_answer}"
                
Now guide them up to L1 by building on their understanding:
- Use their answer to frame the next level up
- Connect to broader concepts in {current_status.get('subtopic', last_concept)}
- Use encouraging language: "Nice! With that in mind..." or "Great! Using your idea of..."
- Help them see the bigger picture
                
Ask just the L1 question that builds on their understanding."""
            else:
                prompt = f"""The user struggled with the L0 question about the subtopic: "{current_status.get('subtopic', last_concept)}".

Your task is to ask a simpler, foundational L1 question to check their understanding of a core component of that EXACT SAME subtopic.

**CRITICAL RULES:**
1.  Your question MUST be about a term or concept directly within "{current_status.get('subtopic', last_concept)}".
2.  Do NOT switch to a new topic or a general programming concept.
3.  Generate a brief, natural, and supportive intro phrase (3-5 words) before the question. Avoid using the exact same phrase every time.

**Example of a good complete response (if L0 was about loss functions):**
"Okay, let's break that down. What is the difference between a 'prediction' and a 'label'?"

Now, generate your own response for the subtopic "{current_status.get('subtopic', last_concept)}". Ask just the question, framed by your supportive intro.
"""
        
        elif current_status['level'] == 2:
            if self.climbing_up:
                prompt = f"""Excellent! The learner answered correctly at L3: "{self.last_correct_answer}"
                
Now guide them up to L2 by building on their intuitive understanding:
- Use their answer to explain mechanisms/relationships
- Connect to how things work in {current_status.get('subtopic', last_concept)}
- Use encouraging language: "Perfect! Using your intuition..."
- Help them understand the process or connection
                
Ask just the L2 question about mechanisms/relationships."""
            else:
                prompt = f"""The user is still struggling with {current_status.get('subtopic', last_concept)}. 
                
Ask about the mechanism or relationship:
- Focus on how things work or connect
- Use guiding questions: "What do you think happens when..." or "How might these connect..."
- Guide them to think about processes
- Never provide the answer, only guide through questions
- Keep it supportive and encouraging

Ask just the guiding question about the mechanism."""
        
        elif current_status['level'] == 3:
            prompt = f"""This is the most basic level for {current_status.get('subtopic', last_concept)}. 
            
Ask a technical, precise question (NOT layman analogies):
- Focus on fundamental technical concepts
- Use proper technical terminology
- Ask about core mechanisms or principles
- Be specific and precise in your language
- Maintain technical accuracy at this deepest level
- Help them understand the technical foundation

Ask just the technical foundational question."""
        
        else:
            prompt = f"""The learner has reached maximum depth and still struggles. 
            
Give brief encouragement and switch to a completely new subtopic:
- Be supportive: "That's okay, let's try something different..."
- Choose a new subtopic related to {self.user_learning_area if self.user_learning_area else 'their learning area'}
- Start fresh with a new L0 conceptual question
- Keep it encouraging and positive

Ask just the new L0 question for a different subtopic."""
        
        # Generate question using the model
        try:
            response = self.model.generate_content(prompt + f"\n\nRecent conversation: {chat_history[-2:] if chat_history else 'None'}")
            question = response.text.strip()
            
            # Clean up the response to ensure it's just a question
            if "Question:" in question:
                question = question.split("Question:")[-1].strip()
            
            # Prefix ladder level label to non-recovery questions
            # Only add when not in recovery mode; avoid double-prefixing if already present
            label_map = {0: "L0", 1: "L1", 2: "L2", 3: "L3"}
            level_label = label_map.get(current_status.get('level', 0), f"L{current_status.get('level', 0)}")
            upper = question.lstrip().upper()
            already_labeled = any(upper.startswith(f"{lab}:") for lab in ["L0", "L1", "L2", "L3"])
            if not already_labeled:
                question = f"{level_label}: {question}"
            
            return question
            
        except Exception as e:
            # Ensure fallback is also labeled when not in recovery mode
            fallback = f"Let's continue with a question about {self.user_learning_area if self.user_learning_area else 'technical concepts'}. What would you like to explore next?"
            # Re-check status to label appropriately
            status = self.ladder_tracker.get_status()
            if not status.get('recovery_mode', False):
                label_map = {0: "L0", 1: "L1", 2: "L2", 3: "L3"}
                level_label = label_map.get(status.get('level', 0), f"L{status.get('level', 0)}")
                fallback = f"{level_label}: {fallback}"
            return fallback
    
    def _extract_user_learning_area(self, chat_history):
        """Extract the user's stated learning area from their introduction"""
        for message in chat_history:
            if message["role"] == "user":
                user_input = message["content"].lower()
                # Look for learning indicators
                learning_phrases = ["learning", "studying", "working on", "interested in", "focusing on"]
                for phrase in learning_phrases:
                    if phrase in user_input:
                        # Extract the topic after the learning phrase
                        parts = user_input.split(phrase)
                        if len(parts) > 1:
                            topic_part = parts[1].strip()
                            # Clean up common words and extract the main topic
                            topic_part = topic_part.replace("about", "").replace("on", "").strip()
                            if topic_part:
                                # Take the first few words as the learning area
                                self.user_learning_area = topic_part.split()[0:3]  # Take up to 3 words
                                self.user_learning_area = " ".join(self.user_learning_area)
                                break
                break

    def process_user_response(self, user_input, current_question=""):
        """Process user response and extract concepts"""
        keywords = extract_keywords(user_input)
        
        # Try to identify the concept being discussed
        concept = self.memory.identify_concept_from_text(user_input)
        if not concept and current_question:
            concept = self.memory.identify_concept_from_text(current_question)
        if not concept:
            concept = self.current_concept
        
        # Add keywords to memory
        self.memory.add_keywords(keywords, concept)
        
        return concept
    
    def update_progress(self, concept, score):
        """Update ladder tracker with score"""
        # The ladder tracker state is managed in get_next_question method
        self.current_concept = concept
            
    def get_progress_summary(self):
        """Get ladder status summary"""
        return {
            'ladder_status': self.ladder_tracker.get_status()
        }
    
    def should_continue(self):
        """Check if the session should continue"""
        return True
    
    def set_last_feedback_type(self, feedback_type):
        """Store the feedback type from evaluation for ladder decisions"""
        self._last_feedback_type = feedback_type
