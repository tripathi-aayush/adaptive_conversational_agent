import subprocess
import sys
import os

def main():
    """Run the Streamlit interview preparation assistant"""
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("⚠️  Warning: .env file not found!")
        print("Please create a .env file with your GEMINI_API_KEY")
        print("Example: GEMINI_API_KEY=your_api_key_here")
        print()
    
    print("🎯 Starting Interview Preparation Assistant...")
    print("📱 The app will open in your browser automatically")
    print("⏹️  Press Ctrl+C to stop the server")
    print()
    
    try:
        # Run streamlit
        subprocess.run([sys.executable, "-m", "streamlit", "run", "streamlit_app.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Thanks for using the Interview Preparation Assistant!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Streamlit: {e}")
        print("Make sure you have installed the requirements: pip install -r requirements.txt")

if __name__ == "__main__":
    main()
