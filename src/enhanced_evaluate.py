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
            if user_lower in ["", "nah", "skip", "i don't know", "idk"]:
                correct_answer = self._get_correct_answer(question, concept, score=0)
                return 0, "No answer provided.", correct_answer, "zero_knowledge"
        
        # --- THIS IS THE UPDATED PART ---
        # The persona is now a "friendly tutor" and the scoring is explicitly lenient.
        prompt = f"""
You are a friendly and encouraging tutor. Your goal is to build the user's confidence.

Question: {question}
Student's answer: {user_answer}

SCORING RULES (Be Lenient!):
- Be generous with points. Award partial credit for any signs of understanding or genuine effort.
- If the user is on the right track at all, give them a score above 60.
- Only give a score below 40 if the answer is completely unrelated to the question.

FEEDBACK RULES:
- Always be positive and encouraging.
- For high scores (≥ 80), praise them (e.g., "Excellent!", "Great answer!").
- For medium scores (60-79), start with encouragement and then give a small hint for improvement (e.g., "Good start! To make it perfect, also mention...").
- For low scores (< 60), be gentle and focus on the core concept they missed (e.g., "That's a common point of confusion. The key idea to remember is...").

CRITICAL: Always provide BOTH a score, feedback, AND the correct answer.

Format:
Score: <number>
Feedback: <your encouraging feedback>
Answer: <the correct answer, explained clearly for a learner>
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
            detail_instruction = "Give a concise 1-2 line answer, like a quick confirmation."
        else:
            detail_instruction = "Give a detailed paragraph explanation for a learner."
        
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