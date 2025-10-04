from enhanced_chatbot import EnhancedChatbot
from enhanced_evaluate import EnhancedEvaluator
import os

def load_prompt(filename="prompts/enhanced_system_prompt.txt"):
    """Load the system prompt"""
    try:
        with open(filename, "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        return """You are an intelligent, interactive interview preparation assistant."""

def print_separator():
    """Print a visual separator"""
    print("=" * 60)

def print_score_feedback(score, feedback, feedback_type):
    """Print formatted score and feedback"""
    print_separator()
    
    if score >= 80:
        score_color = "Excellent"
    elif score >= 60:
        score_color = "Good"
    elif score >= 40:
        score_color = "Needs Work"
    else:
        score_color = "Keep Trying"
    
    print(f" SCORE: {score}/100 ({score_color})")
    
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
    
    chatbot = EnhancedChatbot()
    evaluator = EnhancedEvaluator()
    chat_history = []
    
    print("Let's start! Please introduce yourself and mention your technical background:")
    intro = input("👤 You: ").strip()
    
    if intro.lower() in ['quit', 'exit', 'stop']:
        print("👋 Goodbye! Come back anytime to continue learning.")
        return
    
    print()
    chat_history.append({"role": "user", "content": intro})
    
    question_count = 0
    last_score = None
    last_concept = None
    
    print("🚀 Great! Let's begin your session...\n")
    
    while True:
        try:
            bot_message = chatbot.get_next_question(chat_history, last_score, last_concept)
            question = bot_message['content']
            
            print(f"🤖 Interviewer: {question}")
            chat_history.append(bot_message)
            
            user_reply = input("👤 You: ").strip()
            
            if user_reply.lower() in ['quit', 'exit', 'stop']:
                break
            
            if not user_reply:
                print("Please provide an answer, or type 'quit' to exit.\n")
                continue
            
            print()
            
            chat_history.append({"role": "user", "content": user_reply})

            # --- THIS IS THE UPDATED PART ---
            # We check the 'evaluate' flag from the bot's last message
            should_evaluate = bot_message.get('evaluate', True) # Default to True

            if should_evaluate:
                # Normal evaluation for technical questions
                score, feedback, correct_answer, feedback_type = evaluator.evaluate_answer(
                    user_reply, question,
                )
                
                chatbot.set_last_feedback_type(feedback_type)

                if feedback_type == "clarification_request":
                    print(f"Okay, let me rephrase...")
                    last_score = None
                    continue
                
                if score is None:
                    print("Could not determine a score. Let's try another question.")
                    last_score = None
                    continue

                print_score_feedback(score, feedback, feedback_type)
                
                if correct_answer and correct_answer.strip():
                    print(f"✅ CORRECT ANSWER: {correct_answer}\n")
                
                last_score = score
                last_concept = chatbot.process_user_response(user_reply, question)
                question_count += 1
            
            else:
                # If evaluate is False, we skip scoring entirely
                print("Okay, let's move on.")
                # If the user suggests a new topic, add it to the queue
                if user_reply.lower() not in ["no", "nah", "stop", "quit"]:
                     chatbot.topic_queue.append(('user_mentioned', user_reply))
                # Reset score to start the next topic fresh at L0
                last_score = None

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