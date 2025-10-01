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

# Custom CSS for better UI
st.markdown("""
<style>
    /* Hides the Streamlit toolbar containing the GitHub icon */
    div[data-testid="stToolbar"] {
        visibility: hidden;
        height: 0%;
        position: fixed;
    }
    .main-header {
        text-align: center;
        color: #2E86AB;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
        border-left: 4px solid #2E86AB;
        color: white;
        background-color: #0400e8;
    }
    .score-display {
        background: linear-gradient(90deg, #2E86AB, #A23B72);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        text-align: center;
        font-weight: bold;
        margin: 1rem 0;
    }
    .feedback-section {
        color: var(--text-color);
        background-color: var(--secondary-background-color);
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .answer-section {
        color: var(--text-color);
        background-color: var(--secondary-background-color);
        border: 1px solid #A23B72;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .ladder-status {
        color: var(--text-color);
        background-color: #fff3e0;
        padding: 0.5rem;
        border-radius: 5px;
        font-size: 0.9rem;
        margin-bottom: 1rem;
    }
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: transparent;
        color: var(--text-color);
        opacity: 0.7;
        text-align: center;
        padding: 10px;
        font-size: 0.9em;
    }
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

def main():
    # Header
    st.markdown('<h1 class="main-header">🎯 Interview Preparation Assistant</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #666;">Master technical concepts through a dynamic, bidirectional learning ladder.</p>', unsafe_allow_html=True)
    
    # Sidebar for controls
    with st.sidebar:
        st.header("Session Controls")
        
        # Display ladder status
        if st.session_state.session_started:
            progress = st.session_state.chatbot.get_progress_summary()
            ladder_status = progress.get('ladder_status', {})
            level = ladder_status.get('level', 0)
            
            # Format level display for L+
            level_display = f"L{'+' if level > 0 else ''}{level}"
            
            st.markdown(f"""
            <div class="ladder-status">
                <strong>Current Status:</strong><br>
                Topic: {ladder_status.get('subtopic', 'None')}<br>
                Difficulty Level: {level_display}<br>
                Questions Asked: {st.session_state.question_count}<br>
                Topics in Queue: {len(st.session_state.chatbot.topic_queue)}
            </div>
            """, unsafe_allow_html=True)
        
        # Reset button
        if st.button("🔄 Reset Session", type="secondary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Main content area
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col2:
        # Session initialization
        if not st.session_state.session_started:
            st.markdown("### Welcome! Let's begin.")
            st.markdown("Introduce yourself and mention up to 3 technical areas you're interested in:")
            
            intro = st.text_area(
                "Your introduction:",
                placeholder="Hi, I'm a student focusing on machine learning, convex optimization, and UAV communication...",
                height=100
            )
            
            if st.button("🚀 Start Session", type="primary"):
                if intro.strip():
                    st.session_state.chat_history.append({"role": "user", "content": intro})
                    st.session_state.session_started = True
                    
                    bot_message = st.session_state.chatbot.get_next_question(
                        st.session_state.chat_history,
                        st.session_state.last_score,
                        st.session_state.last_concept
                    )
                    st.session_state.chat_history.append(bot_message)
                    st.rerun()
                else:
                    st.error("Please provide an introduction to get started!")
        
        else:
            # Display chat history
            for i, message in enumerate(st.session_state.chat_history):
                if message["role"] == "user":
                    st.markdown(f"""
                    <div class="chat-message" style="background-color: #06402B; border-left-color: #4CAF50; color: white;">
                        <strong>You:</strong> {message["content"]}
                    </div>
                    """, unsafe_allow_html=True)
                elif message["role"] == "assistant":
                    st.markdown(f"""
                    <div class="chat-message">
                        <strong>Interviewer:</strong> {message["content"]}
                    </div>
                    """, unsafe_allow_html=True)
            
            # Answer input
            st.markdown("### Your Answer:")
            answer = st.text_area(
                "Type your response:",
                placeholder="Enter your answer here...",
                height=150,
                key="answer_input"
            )
            
            button_col, spinner_col = st.columns([1, 3])

            with button_col:
                submit_clicked = st.button("📤 Submit Answer", type="primary")

            if submit_clicked:
                if answer.strip():
                    with spinner_col:
                        with st.spinner("Analyzing your answer..."):
                            current_question = st.session_state.chat_history[-1]['content']
                            # Process response to extract new keywords for the queue
                            concept = st.session_state.chatbot.process_user_response(answer, current_question)
                            st.session_state.chat_history.append({"role": "user", "content": answer})
                            
                            # Evaluate the answer
                            score, feedback, correct_answer, feedback_type = st.session_state.evaluator.evaluate_answer(
                                answer, current_question, concept
                            )
                            
                            st.session_state.chatbot.set_last_feedback_type(feedback_type)
                            
                            # Handle clarification requests
                            if feedback_type == "clarification_request":
                                st.session_state.last_score = None
                                rephrased_message = st.session_state.chatbot.get_next_question(st.session_state.chat_history)
                                st.session_state.chat_history.append(rephrased_message)
                                st.rerun()
                            
                            st.session_state.last_score = score
                            st.session_state.last_concept = concept
                            st.session_state.question_count += 1

                            # Display results
                            if score is not None:
                                st.session_state.display_score = score
                            if feedback:
                                st.session_state.display_feedback = feedback
                            if correct_answer:
                                st.session_state.display_correct_answer = correct_answer
                            
                            # Get the next question based on the new logic
                            next_bot_message = st.session_state.chatbot.get_next_question(
                                st.session_state.chat_history,
                                st.session_state.last_score,
                                st.session_state.last_concept
                            )
                            st.session_state.chat_history.append(next_bot_message)
                    
                    st.rerun()
                else:
                    st.error("Please provide an answer!")

            # Display evaluation results
            if 'display_score' in st.session_state and st.session_state.display_score is not None:
                st.markdown(f'<div class="score-display">Score: {st.session_state.display_score}/100</div>', unsafe_allow_html=True)
                del st.session_state.display_score
            
            if 'display_feedback' in st.session_state and st.session_state.display_feedback:
                st.markdown(f"""
                <div class="feedback-section">
                    <strong>💬 Feedback:</strong><br>
                    {st.session_state.display_feedback}
                </div>
                """, unsafe_allow_html=True)
                del st.session_state.display_feedback

            if 'display_correct_answer' in st.session_state and st.session_state.display_correct_answer:
                st.markdown(f"""
                <div class="answer-section">
                    <strong>✅ Correct Answer:</strong><br>
                    {st.session_state.display_correct_answer}
                </div>
                """, unsafe_allow_html=True)
                del st.session_state.display_correct_answer

    # Footer
    st.markdown("""
        <div class="footer">
            © Interview Preparation Assistant | Built with <a href="https://streamlit.io" target="_blank" style="color: #888;">Streamlit</a>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()