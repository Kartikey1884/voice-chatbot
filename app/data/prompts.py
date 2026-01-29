"""
System Prompts and Prompt Templates
Centralized prompt management for the AI assistant
"""

import json
from typing import Dict, Any


def load_user_data(file_path: str = None) -> Dict[str, Any]:
    """Load user data from JSON file"""
    from app.core.config import settings
    
    if file_path is None:
        file_path = settings.DATA_DIR / "user_details.json"
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {file_path} not found. Using empty user data.")
        return {}


def build_system_prompt(user_data: Dict[str, Any]) -> str:
    """
    Create system prompt with user context
    
    Args:
        user_data: User profile and company information
        
    Returns:
        Complete system prompt string
    """
    
    # Extract key user information safely
    user_profile = user_data.get("userProfile", {})
    personal_info = user_profile.get("personalInfo", {})
    leave_balance = user_data.get("leaveBalance", {})
    first_name = personal_info.get("firstName", "User")
    
    # Extract leave balances
    annual_remaining = leave_balance.get("annualLeave", {}).get("remaining", 0)
    sick_remaining = leave_balance.get("sickLeave", {}).get("remaining", 0)
    casual_remaining = leave_balance.get("casualLeave", {}).get("remaining", 0)
    
    prompt = f"""You are a helpful company assistant with employee data access.

EMPLOYEE DATA:
{json.dumps(user_data, indent=2)}

VOICE CONVERSATION RULES:
- respond in the same language as the user. 
- Keep responses SHORT (1-2 sentences max for voice mode)
- Use employee name: {first_name}
- Answer from JSON data when available
- For questions about leave balance, salary, projects → use JSON directly
- Be conversational and natural
- Avoid long explanations in voice mode

TEXT CONVERSATION RULES:
- respond in the same language as the user.
- only support english language or any Indian languages.
- For text mode, you can provide more detailed responses
- Use formatting when helpful (but don't overuse it)
- Maintain professional yet friendly tone

LEAVE APPLICATION WORKFLOW:
When user wants to apply for leave, follow this step-by-step process:
1. Ask: "How many days of leave do you need?"
2. Validate against available balance:
   - Annual Leave: {annual_remaining} days remaining
   - Sick Leave: {sick_remaining} days remaining
   - Casual Leave: {casual_remaining} days remaining
3. Ask: "When would you like your leave to start? (Please provide the date)"
4. Ask: "What's the reason for your leave?"
5. Generate a formatted leave application with all details

IMPORTANT:
- Ask ONE question at a time for better voice conversation flow.
- don't repeat the generated application back to the user, just generate a leave application.
CURRENT CAPABILITIES:
- Check leave balances
- Apply for leave
- View employee information
- Answer company-related queries
- Provide project information
"""
    
    return prompt


# Alternative: Short prompt for quick responses
def create_quick_prompt(user_data: Dict[str, Any]) -> str:
    """Create a shorter prompt for faster responses"""
    
    user_profile = user_data.get("userProfile", {})
    personal_info = user_profile.get("personalInfo", {})
    first_name = personal_info.get("firstName", "User")
    
    return f"""You are {first_name}'s assistant. Answer questions about their work profile, leave balance, and projects. Keep responses under 2 sentences for voice mode. Data: {json.dumps(user_data)}"""
