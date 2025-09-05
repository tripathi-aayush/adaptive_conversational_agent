from enhanced_chatbot import EnhancedChatbot
from enhanced_evaluate import EnhancedEvaluator
import os

def load_prompt(filename="prompts/enhanced_system_prompt.txt"):
    """Load the system prompt"""
    try:
        with open(filename, "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        return """You are an intelligent, interactive interview preparation assistant. 
Your goal is to help users master technical concepts through targeted questioning, 
accurate feedback, and guided learning. Be encouraging, adaptive, and educational."""

def print_separator():
    """Print a visual separator"""
    print("=" * 60)

def print_score_feedback(score, feedback, feedback_type):
    """Print formatted score and feedback"""
    print_separator()
    
    # Score with emoji
    if score >= 80:
        score_color = "Excellent"
    elif score >= 60:
        score_color = "Good"
    elif score >= 40:
        score_color = "Needs Work"
    else:
        score_color = "Keep Trying"
    
    print(f" SCORE: {score}/100 ({score_color})")
    
    # Minimal feedback for high scores, detailed for low scores
    if score >= 80:
        if feedback and feedback.lower() not in ['correct', 'good']:
            print(f"💬 {feedback}")
    else:
        print(f"\n💬 FEEDBACK:")
        feedback_lines = feedback.split('\n')
        for line in feedback_lines:
            if line.strip():
                print(f"   {line.strip()}")
    
    print_separator()

def main():
    """Main interactive learning session"""
    print("🎓 Welcome to your AI Interview Preparation Assistant!\n")
    print("Type 'quit', 'exit', or 'stop' anytime to end the session.\n")
    
    # Initialize components
    chatbot = EnhancedChatbot()
    evaluator = EnhancedEvaluator()
    system_prompt = load_prompt()
    
    # Initialize chat history
    chat_history = [{"role": "system", "content": system_prompt}]
    
    # Get introduction
    print("Let's start! Please introduce yourself and mention your technical background:")
    intro = input("👤 You: ").strip()
    
    if intro.lower() in ['quit', 'exit', 'stop']:
        print("👋 Goodbye! Come back anytime to continue learning.")
        return
    
    print()
    chat_history.append({"role": "user", "content": intro})
    chatbot.process_user_response(intro)
    
    question_count = 0
    last_score = None
    last_concept = None
    
    print("🚀 Great! Let's begin your session...\n")
    
    # Main learning loop
    while True:
        try:
            # Get next question
            bot_message = chatbot.get_next_question(chat_history, last_score, last_concept)
            question = bot_message['content']
            
            print(f"🤖 Interviewer: {question}")
            chat_history.append(bot_message)
            
            # Get user response
            user_reply = input("👤 You: ").strip()
            
            # Check for exit conditions
            if user_reply.lower() in ['quit', 'exit', 'stop']:
                break
            
            if not user_reply:
                print("Please provide an answer, or type 'quit' to exit.\n")
                continue
            
            print()  # Add spacing
            
            # Process response and get concept
            concept = chatbot.process_user_response(user_reply, question)
            chat_history.append({"role": "user", "content": user_reply})
            
            # This ensures no score/feedback/correct-answer appears and prevents ladder logic from using a score.
            ladder_status = chatbot.get_progress_summary().get('ladder_status', {})
            if ladder_status.get('recovery_mode'):
                # Do not evaluate, do not set last_score
                last_score = None
                last_concept = concept  # keep concept memory if any
                question_count += 1
                # Immediately move to next off-topic question
                continue
            
            # Evaluate the answer
            score, feedback, correct_answer, feedback_type = evaluator.evaluate_answer(
                user_reply, question, concept, 
            )
            
            chatbot.set_last_feedback_type(feedback_type)

            if feedback_type == "clarification_request":
                print(f"... {feedback}") # Prints "Clarification requested" or similar
                last_score = None # Ensure no score is carried over
                continue # Skip to the next loop to get the rephrased question
            
            print_score_feedback(score, feedback, feedback_type)
            
            if correct_answer and correct_answer.strip():
                print(f"✅ CORRECT ANSWER: {correct_answer}\n")
            
            # Update progress
            if concept:
                chatbot.update_progress(concept, score)
            
            # Store for next iteration
            last_score = score
            last_concept = concept
            question_count += 1
            
        except KeyboardInterrupt:
            print("\n\n⏸️  Session interrupted.")
            break
        except Exception as e:
            print(f"❌ An error occurred: {e}")
            print("Let's continue with the next question.\n")
    
    print("\n🎯 Session Complete!")
    print(f"📈 Total questions answered: {question_count}")
    print("\n👋 Great work! Come back anytime to continue learning!")

if __name__ == "__main__":
    main()
