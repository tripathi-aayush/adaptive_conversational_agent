import streamlit as st
import os
from dotenv import load_dotenv
from enhanced_chatbot import EnhancedChatbot
from enhanced_evaluate import EnhancedEvaluator
import time

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Interview Preparation Assistant",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Typing effect generator
def stream_text(text):
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.04)

# --- Custom Modern CSS ---
st.markdown("""
<style>
    /* Hide toolbar */
    div[data-testid="stToolbar"] {visibility: hidden; height: 0%; position: fixed;}

    /* HEADER */
    .main-header {
        text-align: center;
        margin-bottom: 1rem;
        font-size: clamp(1.5rem, 3vw, 2.2rem); /* balanced size */
        font-weight: 800;
    }
    .main-header .emoji {
        font-size: 1.8rem;
        margin-right: 0.4rem;
    }
    .main-header .gradient-text {
        background: linear-gradient(90deg, #2E86AB, #A23B72);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: inline-block;
    }

    .sub-header {
        text-align: center;
        color: #555;
        font-size: clamp(1rem, 2vw, 1.2rem);
        margin-bottom: 2rem;
    }

    /* CHAT BUBBLES */
    .chat-bubble-user {
        background-color: #2E86AB;
        color: white;
        padding: 0.8rem 1rem;
        border-radius: 12px;
        margin: 0.5rem 0;
        max-width: 80%;
        align-self: flex-end;
        box-shadow: 0 2px 5px rgba(0,0,0,0.15);
    }
    .chat-bubble-bot {
        background-color: #f4f4f4;
        color: #222;
        padding: 0.8rem 1rem;
        border-radius: 12px;
        margin: 0.5rem 0;
        max-width: 80%;
        align-self: flex-start;
        box-shadow: 0 2px 5px rgba(0,0,0,0.15);
    }

    /* SCORE BADGE */
    .score-display {
        background: linear-gradient(90deg, #2E86AB, #A23B72);
        color: white;
        padding: 0.7rem 1.2rem;
        border-radius: 30px;
        text-align: center;
        font-weight: bold;
        margin: 1.5rem 0;
        font-size: clamp(1rem, 2vw, 1.3rem);
        box-shadow: 0 3px 8px rgba(0,0,0,0.2);
    }

    /* FEEDBACK BOX */
    .stExpander {
        border: 1px solid #ddd !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08) !important;
        margin-bottom: 1rem;
    }

    /* BUTTONS */
    .stButton button {
        border-radius: 8px;
        background: linear-gradient(90deg, #2E86AB, #A23B72);
        color: white;
        font-weight: 600;
        padding: 0.6rem 1.2rem;
        border: none;
        transition: 0.3s;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    }

    /* FOOTER */
    .footer {
        text-align: center;
        color: #666;
        margin-top: 2rem;
        font-size: 0.9rem;
        opacity: 0.8;
    }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown(
    '<h1 class="main-header"><span class="emoji">🎯</span><span class="gradient-text">Interview Preparation Assistant</span></h1>',
    unsafe_allow_html=True
)

st.markdown('<p class="sub-header">Master technical concepts through a dynamic learning ladder.</p>', unsafe_allow_html=True)

# --- Universal session state initializer ---
defaults = {
    "chatbot": None,
    "evaluator": None,
    "chat_history": [],
    "session_started": False,
    "question_count": 0,
    "last_score": None,
    "last_concept": None,
    "error_message": None,
}
for key, default in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Initialize heavy objects only once
if st.session_state.chatbot is None:
    st.session_state.chatbot = EnhancedChatbot()
if st.session_state.evaluator is None:
    st.session_state.evaluator = EnhancedEvaluator()

def main():
        
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Session Controls")
        
        if st.session_state.session_started:
            progress = st.session_state.chatbot.get_progress_summary()
            ladder_status = progress.get('ladder_status', {})
            level = ladder_status.get('level', 0)
            level_display = f"L{'+' if level > 0 else ''}{level}"
            progress_value = (level + 3) / 6.0
            st.progress(progress_value, text=f"Difficulty Level: {level_display}")

            st.info(f"**Topic:** {ladder_status.get('subtopic','None')}\n\n"
                    f"**Questions Asked:** {st.session_state.question_count}\n\n"
                    f"**Topics in Queue:** {len(st.session_state.chatbot.topic_queue)}")

        if st.button("🔄 Reset Session"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # MAIN UI
    if not st.session_state.session_started:
        st.markdown("### 👋 Welcome! Let's begin.")
        intro = st.text_area("Introduce yourself and mention your areas of interest:")
        
        if st.button("🚀 Start Session"):
            if intro.strip():
                st.session_state.chat_history.append({"role": "user", "content": intro})
                st.session_state.session_started = True
                bot_message = st.session_state.chatbot.get_next_question(st.session_state.chat_history)
                bot_message["streamed"] = False
                st.session_state.chat_history.append(bot_message)
                st.rerun()
            else:
                st.session_state.error_message = "Please provide an introduction to get started!"
    
    else:
        # Chat display
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f"<div class='chat-bubble-user'>{message['content']}</div>", unsafe_allow_html=True)
            else:
                if not message.get("streamed", False):
                    bot_text = "".join([w for w in stream_text(message["content"])])
                    st.markdown(f"<div class='chat-bubble-bot'>{bot_text}</div>", unsafe_allow_html=True)
                    message["streamed"] = True
                else:
                    st.markdown(f"<div class='chat-bubble-bot'>{message['content']}</div>", unsafe_allow_html=True)

        # Score
        if 'display_score' in st.session_state and st.session_state.display_score is not None:
            st.markdown(f'<div class="score-display">Score: {st.session_state.display_score}/100</div>', unsafe_allow_html=True)

        # Feedback
        if 'display_feedback' in st.session_state and st.session_state.display_feedback:
            with st.expander("💬 Detailed Feedback"):
                st.info(st.session_state.display_feedback)

        if 'display_correct_answer' in st.session_state and st.session_state.display_correct_answer:
            with st.expander("✅ Correct Answer"):
                st.success(st.session_state.display_correct_answer)

        # Answer input
        answer = st.text_area("✍️ Your Answer:", height=120, key="answer_input")
        if st.button("📤 Submit Answer"):
            if answer.strip():
                for key in ["display_score", "display_feedback", "display_correct_answer", "error_message"]:
                    if key in st.session_state: del st.session_state[key]
                placeholder = st.empty()
                placeholder.info("Analyzing your answer...")

                current_question_object = st.session_state.chat_history[-1]
                current_question = current_question_object['content']
                should_evaluate = current_question_object.get('evaluate', True)

                st.session_state.chat_history.append({"role": "user", "content": answer})

                if should_evaluate:
                    score, feedback, correct_answer, feedback_type = st.session_state.evaluator.evaluate_answer(answer, current_question)
                    st.session_state.chatbot.set_last_feedback_type(feedback_type)
                    if feedback_type != "clarification_request":
                        st.session_state.last_score = score
                        st.session_state.last_concept = st.session_state.chatbot.process_user_response(answer, current_question)
                        st.session_state.question_count += 1
                    if score is not None: st.session_state.display_score = score
                    if feedback: st.session_state.display_feedback = feedback
                    if correct_answer: st.session_state.display_correct_answer = correct_answer
                else:
                    if answer.strip().lower() not in ["no", "nah", "stop", "quit", "nope", "end"]:
                        st.session_state.chatbot.topic_queue.append(('user_mentioned', answer))
                    st.session_state.last_score = None

                next_bot_message = st.session_state.chatbot.get_next_question(
                    st.session_state.chat_history,
                    st.session_state.last_score,
                    st.session_state.last_concept
                )
                next_bot_message["streamed"] = False
                st.session_state.chat_history.append(next_bot_message)
                st.rerun()
            else:
                st.session_state.error_message = "Please provide an answer!"

        # Error persistent
        if st.session_state.error_message:
            st.error(st.session_state.error_message)

    # Footer
    st.markdown("""
    <div class="footer">
        © 2025 Interview Preparation Assistant | Crafted with ❤️ using 
        <a href="https://streamlit.io" target="_blank">Streamlit</a>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
