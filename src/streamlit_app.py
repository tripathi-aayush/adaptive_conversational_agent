import streamlit as st
import os
from dotenv import load_dotenv
from enhanced_chatbot import EnhancedChatbot
from enhanced_evaluate import EnhancedEvaluator

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Interview Preparation Assistant",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    a[title="View source"] { display: none !important; }
    .main-header { text-align: center; color: #2E86AB; margin-bottom: 2rem; }
    .chat-message { padding: 1rem; margin: 0.5rem 0; border-radius: 10px; border-left: 4px solid #2E86AB; color: white; background-color: #0400e8; }
    .score-display { background: linear-gradient(90deg, #2E86AB, #A23B72); color: white; padding: 0.5rem 1rem; border-radius: 20px; text-align: center; font-weight: bold; margin: 1rem 0; }
    .feedback-section { color: var(--text-color); background-color: var(--secondary-background-color); padding: 1rem; border-radius: 8px; margin: 1rem 0; }
    .answer-section { color: var(--text-color); background-color: var(--secondary-background-color); border: 1px solid #A23B72; padding: 1rem; border-radius: 8px; margin: 1rem 0; }
    .ladder-status { color: var(--text-color); background-color: #fff3e0; padding: 0.5rem; border-radius: 5px; font-size: 0.9rem; margin-bottom: 1rem; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: transparent; color: var(--text-color); opacity: 0.7; text-align: center; padding: 10px; font-size: 0.9em; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'chatbot' not in st.session_state:
    st.session_state.chatbot = EnhancedChatbot()
    st.session_state.evaluator = EnhancedEvaluator()
    st.session_state.chat_history = []
    st.session_state.session_started = False
    st.session_state.question_count = 0
    st.session_state.last_score = None
    st.session_state.last_concept = None
    st.session_state.processing = False
    st.session_state.submitted_answer = ""

def main():
    # Header
    st.markdown('<h1 class="main-header">🎯 Interview Preparation Assistant</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #666;">Master technical concepts through adaptive questioning and guided learning</p>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("Session Controls")
        if st.session_state.session_started:
            progress = st.session_state.chatbot.get_progress_summary()
            ladder_status = progress.get('ladder_status', {})
            st.markdown(f"""
            <div class="ladder-status">
                <strong>Ladder Status:</strong><br>
                Level: L{ladder_status.get('level', 0)}<br>
                Subtopic: {ladder_status.get('subtopic', 'None')}<br>
                Questions: {st.session_state.question_count}<br>
                Recovery: {'ON' if ladder_status.get('recovery_mode') else 'OFF'}{f" ({ladder_status.get('recovery_remaining', 0)} left)" if ladder_status.get('recovery_mode') else ''}
            </div>
            """, unsafe_allow_html=True)
        st.markdown("---")
        if st.button("🔄 Reset Session", type="primary", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Main content area
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        if not st.session_state.session_started:
            st.markdown("### Welcome! Let's start your interview.")
            st.markdown("Introduce yourself and mention your technical background :")
            intro = st.text_area("Your introduction:", placeholder="Hi, I'm...", height=100)
            if st.button("🚀 Start Session", type="primary"):
                if intro.strip():
                    st.session_state.chat_history.append({"role": "user", "content": intro})
                    st.session_state.chatbot.process_user_response(intro)
                    st.session_state.session_started = True
                    bot_message = st.session_state.chatbot.get_next_question(st.session_state.chat_history, None, None)
                    st.session_state.chat_history.append(bot_message)
                    st.rerun()
                else:
                    st.error("Please provide an introduction to get started!")
        else:
            # Display chat history
            for message in st.session_state.chat_history:
                if message["role"] == "user":
                    st.markdown(f'''<div class="chat-message" style="background-color: #06402B; border-left-color: #4CAF50; color: white;"><strong>You:</strong> {message["content"]}</div>''', unsafe_allow_html=True)
                elif message["role"] == "assistant":
                    st.markdown(f'''<div class="chat-message"><strong>Interviewer:</strong> {message["content"]}</div>''', unsafe_allow_html=True)

            # The callback now only saves the submitted answer and sets a flag
            def handle_submission():
                if st.session_state.answer_input.strip():
                    st.session_state.submitted_answer = st.session_state.answer_input
                    st.session_state.processing = True
                    st.session_state.answer_input = "" # Clear the input box immediately
                else:
                    st.error("Please provide an answer!")

            # UI Elements
            st.markdown("### Your Answer:")
            st.text_area("Type your response:", placeholder="Enter your answer here...", height=100, key="answer_input")

            button_col, status_col = st.columns([1, 4])
            with button_col:
                # This is now the ONLY submit button
                st.button("📤 Submit Answer", type="primary", on_click=handle_submission)

            # Check for the processing flag set by the callback
            if st.session_state.processing:
                with status_col:
                    with st.spinner("Thinking..."):
                        # Retrieve the stored answer
                        answer = st.session_state.submitted_answer
                        current_question = st.session_state.chat_history[-1]['content']
                        st.session_state.chat_history.append({"role": "user", "content": answer})

                        concept = st.session_state.chatbot.process_user_response(answer, current_question)
                        score, feedback, correct_answer, feedback_type = st.session_state.evaluator.evaluate_answer(answer, current_question, concept)
                        st.session_state.chatbot.set_last_feedback_type(feedback_type)

                        if feedback_type == "clarification_request":
                            st.session_state.last_score = None
                        else:
                            st.session_state.last_score = score
                            st.session_state.last_concept = concept
                            st.session_state.question_count += 1
                            if concept: st.session_state.chatbot.update_progress(concept, score)

                            # Set display variables for the next run
                            if score is not None: st.session_state.display_score = score
                            if feedback: st.session_state.display_feedback = feedback
                            if correct_answer: st.session_state.display_correct_answer = correct_answer

                        # Get the next question and update history
                        next_bot_message = st.session_state.chatbot.get_next_question(st.session_state.chat_history, st.session_state.last_score, st.session_state.last_concept)
                        st.session_state.chat_history.append(next_bot_message)

                        # Reset flags and rerun to display the new state
                        st.session_state.processing = False
                        st.session_state.submitted_answer = ""
                        st.rerun()

            # Display results from the previous run
            if 'display_score' in st.session_state and st.session_state.display_score is not None:
                st.markdown(f'<div class="score-display">Score: {st.session_state.display_score}/100</div>', unsafe_allow_html=True)
                del st.session_state.display_score

            if 'display_feedback' in st.session_state and st.session_state.display_feedback:
                st.markdown(f'''<div class="feedback-section"><strong>💬 Feedback:</strong><br>{st.session_state.display_feedback}</div>''', unsafe_allow_html=True)
                del st.session_state.display_feedback

            if 'display_correct_answer' in st.session_state and st.session_state.display_correct_answer:
                st.markdown(f'''<div class="answer-section"><strong>✅ Correct Answer:</strong><br>{st.session_state.display_correct_answer}</div>''', unsafe_allow_html=True)
                del st.session_state.display_correct_answer

    # Footer
    st.markdown("""<div class="footer">© Interview Preparation Assistant | Built with <a href="https://streamlit.io" target="_blank" style="color: #888;">Streamlit</a></div>""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
