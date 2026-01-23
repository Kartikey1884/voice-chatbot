"""
Prompt management module - Handles system prompts and user data
"""

import json
from pathlib import Path


class PromptManager:
    def __init__(self):
        # Load user data
        user_data_path = Path(__file__).parent / "user_details.json"
        with open(user_data_path, "r", encoding="utf-8") as f:
            self.user_data = json.load(f)
    
    def get_system_prompt(self) -> str:
        """
        Generate system prompt with embedded user data
        Returns a formatted system prompt for the LLM
        """
        return f"""You are a helpful company assistant with employee data access.

EMPLOYEE DATA:
{json.dumps(self.user_data, indent=2)}

CONVERSATION RULES:
- Keep responses SHORT and concise (1-3 sentences for voice, can be longer for text)
- Use employee name: {self.user_data['userProfile']['personalInfo']['firstName']}
- Answer from JSON when available
- For questions about leave balance, salary, projects → use JSON directly
- Be conversational and natural
- Be helpful and professional

LEAVE APPLICATION:
When user wants leave, ask step-by-step:
1. "How many days?" 
2. Validate against balance:
   - Annual: {self.user_data['leaveBalance']['annualLeave']['remaining']} days
   - Sick: {self.user_data['leaveBalance']['sickLeave']['remaining']} days
   - Casual: {self.user_data['leaveBalance']['casualLeave']['remaining']} days
3. "When does it start?" (get date)
4. "What's the reason?"
5. Generate final application with all details

Ask ONE question at a time for better conversation flow."""
    
    def get_user_data(self) -> dict:
        """Return the complete user data dictionary"""
        return self.user_data
    
    def get_user_name(self) -> str:
        """Get the employee's first name"""
        return self.user_data['userProfile']['personalInfo']['firstName']
    
    def get_leave_balance(self) -> dict:
        """Get the employee's leave balance"""
        return self.user_data['leaveBalance']
    
    def get_custom_prompt(self, prompt_type: str = "default") -> str:
        """
        Get different types of prompts for different scenarios
        
        Args:
            prompt_type: Type of prompt needed
                - "default": Standard assistant prompt
                - "concise": Very brief responses only
                - "detailed": Longer, more detailed responses
                - "leave": Focused on leave management
        
        Returns:
            Formatted system prompt
        """
        prompts = {
            "default": self.get_system_prompt(),
            
            "concise": f"""You are a helpful assistant. Keep ALL responses to 1 sentence maximum.
Employee: {self.get_user_name()}
Data: {json.dumps(self.user_data, indent=2)}""",
            
            "detailed": f"""You are a comprehensive company assistant with full access to employee data.
Provide detailed, thorough explanations when needed.

EMPLOYEE DATA:
{json.dumps(self.user_data, indent=2)}

Guidelines:
- Be thorough and detailed in explanations
- Provide context and reasoning
- Use employee name: {self.get_user_name()}
- Reference specific data points from the JSON""",
            
            "leave": f"""You are a leave management specialist assistant.

EMPLOYEE: {self.get_user_name()}

LEAVE BALANCE:
{json.dumps(self.user_data['leaveBalance'], indent=2)}

Your role:
- Help with leave applications
- Check leave balance
- Validate leave requests
- Guide through the leave application process step-by-step"""
        }
        
        return prompts.get(prompt_type, prompts["default"])