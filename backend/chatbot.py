"""
Chatbot module - Handles LLM interaction with Groq
"""

import os
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv

from prompt import PromptManager

# Load .env from project root
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)


class ChatBot:
    def __init__(self, prompt_type: str = "default"):
        """
        Initialize the chatbot with Groq client
        
        Args:
            prompt_type: Type of prompt to use ("default", "concise", "detailed", "leave")
        """
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"
        self.sessions = {}
        
        # Initialize prompt manager
        self.prompt_manager = PromptManager()
        self.prompt_type = prompt_type
        self.system_prompt = self.prompt_manager.get_custom_prompt(prompt_type)
    
    def set_prompt_type(self, prompt_type: str):
        """
        Change the prompt type dynamically
        
        Args:
            prompt_type: New prompt type to use
        """
        self.prompt_type = prompt_type
        self.system_prompt = self.prompt_manager.get_custom_prompt(prompt_type)
    
    async def stream_response(self, message: str, session_id: str):
        """
        Stream LLM response from Groq
        Yields text chunks as they arrive
        
        Args:
            message: User's input message
            session_id: Unique session identifier for conversation history
        
        Yields:
            str: Text chunks from the LLM response
        """
        # Build messages with history
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add conversation history (last 10 messages)
        history = self.sessions.get(session_id, [])
        messages.extend(history[-10:])
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Stream from Groq
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=500,
            stream=True
        )
        
        full_response = ""
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                yield content
        
        # Save to history
        self.sessions.setdefault(session_id, []).extend([
            {"role": "user", "content": message},
            {"role": "assistant", "content": full_response}
        ])
    
    async def get_response(self, message: str, session_id: str) -> str:
        """
        Get complete response (non-streaming version)
        
        Args:
            message: User's input message
            session_id: Unique session identifier
        
        Returns:
            str: Complete response from LLM
        """
        full_response = ""
        async for chunk in self.stream_response(message, session_id):
            full_response += chunk
        return full_response
    
    def get_conversation_history(self, session_id: str) -> list:
        """
        Get conversation history for a session
        
        Args:
            session_id: Session identifier
        
        Returns:
            list: List of message dictionaries
        """
        return self.sessions.get(session_id, [])
    
    def clear_session(self, session_id: str):
        """
        Clear conversation history for a session
        
        Args:
            session_id: Session identifier to clear
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def clear_all_sessions(self):
        """Clear all conversation histories"""
        self.sessions.clear()
    
    def get_user_data(self) -> dict:
        """Get user data from prompt manager"""
        return self.prompt_manager.get_user_data()
    
    def get_user_name(self) -> str:
        """Get employee name from prompt manager"""
        return self.prompt_manager.get_user_name()
    
    def get_active_sessions(self) -> list:
        """Get list of active session IDs"""
        return list(self.sessions.keys())