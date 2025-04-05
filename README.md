# AI Chat Assistant with Memory

![Python Version](https://img.shields.io/badge/python-3.11.11-blue.svg)
![Streamlit Version](https://img.shields.io/badge/streamlit-1.44.1-red.svg)
![Agno Version](https://img.shields.io/badge/agno-1.2.7-green.svg)

A sophisticated AI chat application with persistent memory capabilities, built with Streamlit and Agno. This application provides a clean, user-friendly interface for interacting with AI while maintaining user-specific memories.

## 🌟 Features

- **Simple User Authentication**: Single username-based login system
- **Chat Interface**: Modern, responsive chat UI with fixed input at bottom
- **Memory System**: AI remembers important information from conversations
- **User-specific Memories**: Memories are tied to specific usernames
- **Conversation Summaries**: Automatic summarization of ongoing chat sessions
- **SQLite Storage**: Persistent storage for user memories
- **Responsive Design**: Works on desktop and mobile devices

## 🚀 Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ai-chat-assistant.git
   cd ai-chat-assistant
   ```

2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   streamlit app.py
   ```

5. Open your browser and navigate to `http://localhost:8501`

## 🔑 User Authentication

The application uses a simple authentication system:
- Users can sign in by entering their name in the username field
- All memories are tied to that username
- To access your memories, sign in with the same username
- No password required (for demonstration purposes)
- Same login button works for both new and returning users

## 💾 Data Storage

The application stores user memories in SQLite databases:
- `data/agent_memory.db`: Stores user memories and conversation summaries
- `data/agent_storage.db`: Stores session information

**Note**: While user memories persist between sessions, chat history is not preserved when you log out. Each login creates a fresh conversation while retaining memories from previous sessions.

## 📋 How It Works

1. **Login**: Enter a username to start
2. **Chat**: Interact with the AI assistant through the chat interface
3. **Memory Creation**: The system automatically creates memories based on important information
4. **Memory Retrieval**: When you log in again with the same username, the AI will remember important information from previous conversations
5. **Summaries**: The AI generates summaries of your current conversation

## 🔧 Technical Details

- **Backend**: Python with Agno framework
- **Frontend**: Streamlit with custom CSS styling
- **Memory System**: Uses Agno's memory management components:
  - `MemoryClassifier`: Identifies important information
  - `MemorySummarizer`: Creates concise summaries of conversations
  - `MemoryManager`: Manages storing and retrieving memories
- **Model**: Integrates with Deepseek AI model via OpenAI-compatible API

## 📱 Mobile Support

The application is designed with a responsive layout that works well on mobile devices:
- Fixed chat input at the bottom of the screen
- Scrollable chat history
- Sidebar that adapts to mobile view

## 🧩 Project Structure

```
.
├── data/                  # SQLite database storage
├── app.py  # Main application file
├── style.css              # Custom styling
├── requirements.txt       # Project dependencies
└── README.md              # Project documentation
```

## 🛠️ Requirements

The application requires Python 3.11+ and the following main packages:
- streamlit==1.44.1
- agno==1.2.7
- sqlalchemy==2.0.40
- python-dotenv==1.0.0
- (See requirements.txt for complete list)

## 📚 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page.

---

Created with ❤️ using Python, Streamlit, and Agno
