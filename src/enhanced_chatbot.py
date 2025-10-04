from keywordextractor import extract_keywords
from ladder_tracker import LadderTracker
import os
from dotenv import load_dotenv
import google.generativeai as genai
import random

# Load .env file
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("No API key found.")

genai.configure(api_key=api_key)

class EnhancedChatbot:
    def __init__(self):
        self.ladder_tracker = LadderTracker()
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite') # Using stable model
        self.conversation_count = 0
        self.session_started = False
        self._last_feedback_type = None
        
        self.topic_queue = []
        self.initial_seeding_done = False

    def get_next_question(self, chat_history, last_score=None, last_concept=None):
        """Get the next question using the new bidirectional ladder and topic queue logic."""
        self.conversation_count += 1
        
        if not self.session_started and chat_history:
            self._seed_initial_topics(chat_history[0]['content'])
            self.session_started = True
        
        if (hasattr(self, '_last_feedback_type') and 
            self._last_feedback_type == "clarification_request"):
            return self._rephrase_current_question(chat_history)
        
        # --- CHANGE 1: This function now expects a dictionary and adds the 'role' ---
        bot_response_object = self._generate_contextual_question(
            chat_history, 
            last_score
        )
        
        bot_response_object['role'] = 'assistant'
        return bot_response_object
    
    def _seed_initial_topics(self, user_intro):
        """Extract up to 3 initial keywords from the user's intro to seed the topic queue."""
        if self.initial_seeding_done:
            return

        try:
            prompt = f"""
Analyze the user's introduction to identify up to 3 core technical topics they mentioned.
USER INTRODUCTION: "{user_intro}"
Instructions:
1. Identify the main technical topics.
2. List up to 3 of the most important ones.
3. Format them as a comma-separated list.
4. If no specific topics are found, return "None".
Topics:
"""
            response = self.model.generate_content(prompt)
            topics_str = response.text.strip()
            
            if topics_str.lower() != 'none':
                topics = [topic.strip() for topic in topics_str.split(',') if topic.strip()]
                for topic in topics[:3]:
                    self.topic_queue.append(('initial', topic))
            self.initial_seeding_done = True
            
        except Exception as e:
            print(f"Error seeding initial topics: {e}")
            self.initial_seeding_done = True

    def _generate_contextual_question(self, chat_history, last_score=None):
        """Generate a question based on the new bidirectional ladder and topic queue."""
        current_status = self.ladder_tracker.get_status()
        topic_source = 'initial'
        
        if hasattr(self, '_last_feedback_type') and self._last_feedback_type == "zero_knowledge":
            self.ladder_tracker.reset_for_new_subtopic()
            current_status = self.ladder_tracker.get_status()

        if current_status['level'] > 0 and last_score is not None and last_score < 60:
            self.ladder_tracker.reset_for_new_subtopic()
            current_status = self.ladder_tracker.get_status()
        elif last_score is not None:
            if last_score >= 60:
                self.ladder_tracker.go_up_ladder()
            else:
                self.ladder_tracker.go_down_ladder()
        
        if not self.ladder_tracker.current_subtopic:
            # --- CHANGE 2: If queue is empty, return the object with the 'evaluate: False' flag. ---
            if not self.topic_queue:
                return {
                    'content': "We've covered all the topics based on our conversation. Would you like to suggest a new area to discuss?",
                    'evaluate': False 
                }
            
            topic_source, topic_name = random.choice(self.topic_queue)
            self.topic_queue.remove((topic_source, topic_name))
            self.ladder_tracker.assign_subtopic(topic_name, reset=True)
        
        current_status = self.ladder_tracker.get_status()
        level = current_status['level']
        subtopic = current_status['subtopic']
        
        prompt_map = {

            3: f"Ask a strategic 'L+3' question about '{subtopic}'. Focus on evaluation, comparison, or practical trade-offs (e.g., scalability, limitations, ethical concerns, integration with other approaches). Avoid academic or research-heavy wording. CRITICAL: Ask only ONE, single, concise question.",
            
            2: f"""You are an interviewer asking a scenario-based 'L+2' question. 
                Build directly on the candidate’s last example or concept, and place it into a practical, real-world situation. 
                Clearly connect the scenario to what the candidate mentioned, and then ask how '{subtopic}' could be applied in that context. 
                Keep the scenario workplace-relevant and approachable. 
                CRITICAL: Your entire response must be just the single question, including the brief scenario.""",

            1: f"""Ask a straightforward conceptual 'L+1' question about '{subtopic}'. 
                Focus on testing understanding of a key idea, method, or sub-concept directly related to it 
                (e.g., definitions, how something works, or differences between related terms). 
                Keep it clear and concise, like a typical follow-up interview question. 
                CRITICAL: Ask only ONE, single, concise question.""",

            0: f"Ask a foundational 'L0' question about '{subtopic}'. This should be a common, core interview question testing basic understanding. CRITICAL: Ask only ONE, single, concise question.",
            
            -1: f"The user is struggling. Ask a simpler 'L-1' question about a key component or prerequisite concept related to '{subtopic}'. CRITICAL: Ask only ONE, single, concise question.",
            
            -2: f"The user needs more help. Ask a very simple 'L-2' definition-based question about a fundamental term within '{subtopic}'. CRITICAL: Ask only ONE, single, concise question.",
            
            -3: f"The user is at the most basic level. Ask an extremely simple 'L-3' confidence-building question (e.g., true/false or very short answer) about '{subtopic}'. CRITICAL: Ask only ONE, single, concise question."
        }

        
        prompt = prompt_map.get(level, prompt_map[0])
        
        if level == 0 and topic_source == 'user_mentioned':
            prompt = f"The user previously mentioned '{subtopic}'. Ask a foundational 'L0' question about it, starting with a phrase like 'You mentioned...'. CRITICAL: Ask only ONE, single, concise question."
        
        prompt += "\n\nCRITICAL: Ask only the question. Be direct and professional."
        
        try:
            response = self.model.generate_content(prompt)
            question = response.text.strip()
            level_label = f"L{'+' if level > 0 else ''}{level}"
            question_content = f"{level_label}: {question}"
            
        except Exception as e:
            question_content = f"L0: Let's switch gears. What can you tell me about {subtopic}?"

        # --- CHANGE 3: All normal questions are now wrapped in a dictionary with 'evaluate: True'. ---
        return {'content': question_content, 'evaluate': True}

    def process_user_response(self, user_input, current_question=""):
        # If the evaluator flags a response as zero_knowledge, we won't extract keywords.
        if hasattr(self, '_last_feedback_type') and self._last_feedback_type == "zero_knowledge":
            return self.ladder_tracker.current_subtopic
            

        new_keywords = extract_keywords(user_input)
        for keyword in new_keywords[:3]:
            if not any(keyword in item for item in self.topic_queue):
                 self.topic_queue.append(('user_mentioned', keyword))
        
        return self.ladder_tracker.current_subtopic
    
    def get_progress_summary(self):
        return { 'ladder_status': self.ladder_tracker.get_status() }

    def set_last_feedback_type(self, feedback_type):
        self._last_feedback_type = feedback_type

    def _rephrase_current_question(self, chat_history):
        """Rephrases the last question upon a clarification request."""
        last_question = ""
        for message in reversed(chat_history):
            if message["role"] == "assistant":
                last_question = message["content"]
                break
        
        prompt = f"""You are a professional technical interviewer. The learner asked for clarification on this question: "{last_question}"

                    Your task is to rephrase the same question more clearly while maintaining a professional and neutral tone.
                    - Keep the same meaning and difficulty level.
                    - Use simpler words if possible.
                    - Do NOT become overly friendly or casual. Maintain the interview context.

                    Provide just the rephrased question"""
        try:
            response = self.model.generate_content(prompt)
            question = response.text.strip()
            original_label = last_question.split(':')[0] if ':' in last_question else 'L0'
            
            # --- CHANGE 4: Add the 'evaluate: True' flag for consistency. ---
            return {
                "role": "assistant",
                "content": f"{original_label}: {question}",
                "evaluate": True 
            }
        except Exception:
            return {
                "role": "assistant",
                "content": last_question,
                "evaluate": True
            }