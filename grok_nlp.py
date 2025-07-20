import os
import json
import re
from datetime import datetime, timedelta
from typing import Tuple, Dict, List, Any
import requests

class GrokNLP:
    def __init__(self):
        """Initialize Grok NLP client for Grok Cloud API"""
        self.api_key = os.getenv('GROK_API_KEY')
        if not self.api_key:
            raise ValueError("GROK_API_KEY environment variable is required")
        
        # Updated base URL for Grok Cloud API
        self.base_url = "https://api.groq.com/openai/v1"  # Corrected URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def extract_event_info(self, user_input: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Extract event information from natural language input
        Returns: (success: bool, result: dict)
        """
        try:
            # Create a detailed prompt for event extraction
            prompt = f"""
            Extract event information from the following text and return a JSON response:
            
            Text: "{user_input}"
            
            Return a JSON object with these fields:
            - title: Event title
            - start_time: ISO format datetime (YYYY-MM-DDTHH:MM:SS)
            - end_time: ISO format datetime (YYYY-MM-DDTHH:MM:SS)
            - duration_minutes: Duration in minutes
            - location: Location (if mentioned, otherwise null)
            - category: Event category (Meeting, Personal, Work, etc.)
            - description: Brief description
            
            Current date/time reference: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            If the text doesn't contain enough information for a valid event, return:
            {{"error": "Insufficient event information"}}
            
            Only return valid JSON, no other text.
            """
            
            # Make API call
            response = self._make_api_call(prompt)
            
            if not response:
                return False, {"error": "Failed to get response from Grok API"}
            
            # Parse JSON response
            try:
                event_data = json.loads(response)
                
                # Check if it's an error response
                if "error" in event_data:
                    return False, event_data
                
                # Validate required fields
                required_fields = ['title', 'start_time', 'end_time', 'duration_minutes']
                missing_fields = [field for field in required_fields if field not in event_data]
                
                if missing_fields:
                    return False, {
                        "error": f"Missing required fields: {', '.join(missing_fields)}"
                    }
                
                # Validate datetime formats
                try:
                    datetime.fromisoformat(event_data['start_time'])
                    datetime.fromisoformat(event_data['end_time'])
                except ValueError as e:
                    return False, {
                        "error": f"Invalid datetime format: {str(e)}"
                    }
                
                return True, event_data
                
            except json.JSONDecodeError as e:
                return False, {
                    "error": f"Invalid JSON response from AI: {str(e)}"
                }
                
        except Exception as e:
            return False, {
                "error": f"Unexpected error: {str(e)}"
            }
    
    def suggest_alternatives(self, event_description: str, conflicts: List[Dict]) -> Tuple[bool, List[Dict]]:
        """
        Suggest alternative times for an event given conflicts
        Returns: (success: bool, suggestions: list)
        """
        try:
            conflict_info = "\n".join([
                f"- {conflict.get('title', 'Event')}: {conflict.get('start', '')} to {conflict.get('end', '')}"
                for conflict in conflicts
            ])
            
            prompt = f"""
            Suggest 3 alternative times for this event: {event_description}
            
            Existing conflicts:
            {conflict_info}
            
            Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            Return a JSON array with 3 alternatives, each containing:
            - suggestion: Human readable suggestion
            - start_time: ISO format datetime
            - end_time: ISO format datetime  
            - reason: Why this time is better
            
            Only return valid JSON array, no other text.
            """
            
            response = self._make_api_call(prompt)
            
            if not response:
                return False, []
            
            try:
                suggestions = json.loads(response)
                
                if not isinstance(suggestions, list):
                    return False, []
                
                # Validate each suggestion
                valid_suggestions = []
                for suggestion in suggestions[:3]:  # Max 3
                    if all(key in suggestion for key in ['suggestion', 'start_time', 'end_time', 'reason']):
                        try:
                            # Validate datetime formats
                            datetime.fromisoformat(suggestion['start_time'])
                            datetime.fromisoformat(suggestion['end_time'])
                            valid_suggestions.append(suggestion)
                        except ValueError:
                            continue  # Skip invalid datetime
                
                return True, valid_suggestions
                
            except json.JSONDecodeError:
                return False, []
                
        except Exception as e:
            print(f"Error in suggest_alternatives: {e}")
            return False, []
    
    def _make_api_call(self, prompt: str) -> str:
        """
        Make API call to Grok Cloud API
        Returns response text or None if failed
        """
        try:
            # Updated payload for Grok Cloud API (uses different model names)
            payload = {
                "model": "llama3-70b-8192",  # Popular Grok Cloud model
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that extracts event information and returns only valid JSON responses."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 1000,
                "stream": False
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            # Add debug information
            print(f"API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return content.strip()
            else:
                print(f"API Error: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except requests.RequestException as e:
            print(f"Request error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error in API call: {e}")
            return None

# Alternative class for testing different Grok Cloud models
class GrokNLPAlternative:
    def __init__(self):
        """Initialize Grok NLP client with alternative settings"""
        self.api_key = os.getenv('GROK_API_KEY')
        if not self.api_key:
            raise ValueError("GROK_API_KEY environment variable is required")
        
        self.base_url = "https://api.groq.com/openai/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def test_connection(self) -> bool:
        """Test the API connection"""
        try:
            payload = {
                "model": "llama3-70b-8192",
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello, respond with just 'OK' if you can hear me."
                    }
                ],
                "max_tokens": 10
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            print(f"Test connection status: {response.status_code}")
            if response.status_code == 200:
                print("✅ Connection successful!")
                return True
            else:
                print(f"❌ Connection failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Connection test error: {e}")
            return False

# Test/Mock version for development
class MockGrokNLP:
    def __init__(self):
        pass
    
    def extract_event_info(self, user_input: str) -> Tuple[bool, Dict[str, Any]]:
        """Mock extraction for testing"""
        try:
            # Simple parsing for common patterns
            user_input = user_input.lower()
            
            # Extract title (simple heuristic)
            title = "Meeting"
            if "lunch" in user_input:
                title = "Lunch"
            elif "call" in user_input:
                title = "Call"
            elif "meeting" in user_input:
                title = "Team Meeting"
            elif "appointment" in user_input:
                title = "Appointment"
            
            # Mock start time (tomorrow 2 PM)
            tomorrow = datetime.now() + timedelta(days=1)
            start_time = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(hours=1)  # 1 hour duration
            
            return True, {
                'title': title,
                'start_time': start_time.strftime('%Y-%m-%dT%H:%M:%S'),
                'end_time': end_time.strftime('%Y-%m-%dT%H:%M:%S'),
                'duration_minutes': 60,
                'location': 'Conference Room A',
                'category': 'Meeting',
                'description': f'Event extracted from: {user_input}'
            }
            
        except Exception as e:
            return False, {
                "error": f"Mock extraction error: {str(e)}"
            }
    
    def suggest_alternatives(self, event_description: str, conflicts: List[Dict]) -> Tuple[bool, List[Dict]]:
        """Mock suggestions for testing"""
        try:
            base_time = datetime.now() + timedelta(days=1)
            
            suggestions = [
                {
                    'suggestion': 'Tomorrow at 3 PM',
                    'start_time': (base_time.replace(hour=15, minute=0, second=0)).strftime('%Y-%m-%dT%H:%M:%S'),
                    'end_time': (base_time.replace(hour=16, minute=0, second=0)).strftime('%Y-%m-%dT%H:%M:%S'),
                    'reason': 'No conflicts at this time'
                },
                {
                    'suggestion': 'Tomorrow at 4 PM', 
                    'start_time': (base_time.replace(hour=16, minute=0, second=0)).strftime('%Y-%m-%dT%H:%M:%S'),
                    'end_time': (base_time.replace(hour=17, minute=0, second=0)).strftime('%Y-%m-%dT%H:%M:%S'),
                    'reason': 'Good time for afternoon meetings'
                }
            ]
            
            return True, suggestions
            
        except Exception as e:
            return False, []

# Quick test function
def test_grok_connection():
    """Test function to verify API connection"""
    try:
        client = GrokNLPAlternative()
        return client.test_connection()
    except Exception as e:
        print(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    # Run connection test
    print("Testing Grok Cloud API connection...")
    test_grok_connection()