import os
from dotenv import load_dotenv
import google.generativeai as genai
import re

# Load .env file
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("No API key found.")

genai.configure(api_key=api_key)

class EnhancedEvaluator:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def evaluate_answer(self, user_answer, question, concept=None, difficulty="intermediate"):
        """Enhanced evaluation with both feedback and correct answer always provided"""
        
        # First, use LLM to classify the response type
        classification_prompt = f"""
Analyze this student response to determine its type:

Question: {question}
Student Response: {user_answer}

Classify the response as ONE of these types:
1. "clarification_request" - Student is confused, asks for repetition, or requests the question in another way
2. "zero_knowledge" - Student explicitly declares no knowledge, says "I don't know", or provides no meaningful attempt
3. "attempt" - Student makes a genuine attempt to answer (even if wrong)

Respond with ONLY the classification type, nothing else.
"""
        
        try:
            classification_response = self.model.generate_content(classification_prompt)
            response_type = classification_response.text.strip().lower()
            
            if "clarification_request" in response_type:
                return None, "Clarification requested", "", "clarification_request"
            elif "zero_knowledge" in response_type:
                correct_answer = self._get_correct_answer(question, concept, score=0)
                return 0, "No answer provided.", correct_answer, "zero_knowledge"
        except Exception as e:
            # Fallback to basic empty check if LLM classification fails
            user_lower = user_answer.strip().lower()
            if user_lower in ["", "nah", "skip"]:
                correct_answer = self._get_correct_answer(question, concept, score=0)
                return 0, "No answer provided.", correct_answer, "zero_knowledge"
        
        # Updated prompt to always generate both feedback AND the answer
        prompt = f"""
You are a technical interviewer giving feedback and the correct answer.

Question: {question}
Student's answer: {user_answer}

CRITICAL: Always provide BOTH feedback AND the correct answer.

Feedback rules:
- Score ≥ 80: Just say "Correct" or "Good" (1-2 words max)
- Score 60-79: Brief hint about what to improve (1 line)
- Score 40-59: Point out the gap (what they missed)
- Score ≤ 39: Identify what's wrong with their response

Answer rules:
- Score > 80: Concise 1-2 line answer (quick confirmation)
- Score ≤ 80: Detailed paragraph explanation for understanding
- Focus on key recall points only, no background history

Format:
Score: <number>
Feedback: <feedback based on score>
Answer: <correct answer with appropriate detail>
"""

        try:
            response = self.model.generate_content(prompt)
            return self._parse_evaluation(response.text, user_answer, question, concept)
        except Exception as e:
            correct_answer = self._get_correct_answer(question, concept, score=25)
            return 25, f"Evaluation error: {e}. Please try again.", correct_answer, "error"
    
    def _parse_evaluation(self, response_text, user_answer, question, concept):
        """Parse the evaluation response to extract score, feedback, and answer"""
        lines = response_text.strip().split('\n')
        
        # Extract score
        score = 50  # default
        for line in lines:
            if line.lower().startswith('score:'):
                try:
                    score = int(re.findall(r'\d+', line)[0])
                except:
                    pass
        
        # Extract feedback
        feedback = ""
        answer = ""
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.lower().startswith('feedback:'):
                current_section = "feedback"
                feedback = line.split(':', 1)[1].strip()
            elif line.lower().startswith('answer:'):
                current_section = "answer"
                answer = line.split(':', 1)[1].strip()
            elif current_section == "feedback" and line and not line.lower().startswith(('score:', 'answer:')):
                feedback += " " + line
            elif current_section == "answer" and line and not line.lower().startswith(('score:', 'feedback:')):
                answer += " " + line
        
        if not answer.strip():
            answer = self._get_correct_answer(question, concept, score)
        
        # Determine feedback type based on score
        if score >= 80:
            feedback_type = "excellent"
        elif score >= 60:
            feedback_type = "good_with_hints"
        elif score >= 40:
            feedback_type = "needs_correction"
        else:
            feedback_type = "needs_detailed_help"
        
        return score, feedback.strip(), answer.strip(), feedback_type
    
    def _get_correct_answer(self, question, concept=None, score=50):
        """Get a correct answer with detail level based on score"""
        if score > 80:
            detail_instruction = "Give a concise 1-2 line answer, like a quick confirmation in an interview."
        else:
            detail_instruction = "Give a detailed paragraph explanation for better understanding."
        
        prompt = f"""
Give the correct answer to: {question}

Requirements:
- {detail_instruction}
- Focus on key recall points only
- No background history or extra theory
- Clear, relevant, and easy to digest
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except:
            return "Let me give you the key points you need to remember."
    
    def generate_follow_up_question(self, concept, difficulty="intermediate", focus_area=None):
        """Generate a follow-up question on the same concept"""
        prompt = f"""
Generate a {difficulty} level follow-up question about: {concept}

{f"Focus specifically on: {focus_area}" if focus_area else ""}

The question should:
- Help reinforce understanding of {concept}
- Be at {difficulty} difficulty level
- Be clear and specific
- Test practical understanding

Provide just the question, no extra text.
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Can you explain more about {concept}?"
