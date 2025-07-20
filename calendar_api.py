import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()

class GoogleCalendarAPI:
    def __init__(self):
        self.SCOPES = [os.getenv('SCOPES', 'https://www.googleapis.com/auth/calendar')]
        self.calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
        self.timezone = pytz.timezone(os.getenv('TIME_ZONE', 'Asia/Kolkata'))
        self.service = None
        self.authenticate()
    
    def authenticate(self):
        """Authenticate and build Google Calendar service"""
        creds = None
        
        # Check if token.json exists (previous authentication)
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
        
        # If no valid credentials, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('calendar', 'v3', credentials=creds)
        print("✅ Google Calendar authenticated successfully!")
    
    def create_event(self, event_data: Dict) -> Tuple[bool, str]:
        """
        Create a calendar event
        
        Args:
            event_data: Dict containing event information
                - title: str
                - start_time: str (ISO format)
                - end_time: str (ISO format)
                - location: str (optional)
                - description: str (optional)
        
        Returns:
            Tuple[bool, str]: (success, message/event_id)
        """
        try:
            # Prepare event body
            event_body = {
                'summary': event_data['title'],
                'start': {
                    'dateTime': event_data['start_time'],
                    'timeZone': str(self.timezone),
                },
                'end': {
                    'dateTime': event_data['end_time'],
                    'timeZone': str(self.timezone),
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': int(os.getenv('DEFAULT_REMINDER_MINUTES', 15))},
                        {'method': 'email', 'minutes': int(os.getenv('DEFAULT_REMINDER_MINUTES', 15))},
                    ],
                },
            }
            
            # Add optional fields
            if event_data.get('location'):
                event_body['location'] = event_data['location']
            
            if event_data.get('description'):
                event_body['description'] = event_data['description']
            
            # Create the event
            event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event_body
            ).execute()
            
            return True, event.get('id')
            
        except HttpError as error:
            return False, f"An error occurred: {error}"
        except Exception as error:
            return False, f"Unexpected error: {error}"
    
    def check_conflicts(self, start_time: str, end_time: str, buffer_minutes: int = None) -> Tuple[bool, List[Dict]]:
        """
        Check for conflicting events in the given time range
        
        Args:
            start_time: ISO format start time
            end_time: ISO format end time
            buffer_minutes: Minutes to add as buffer before/after
        
        Returns:
            Tuple[bool, List[Dict]]: (has_conflicts, list_of_conflicts)
        """
        try:
            if buffer_minutes is None:
                buffer_minutes = int(os.getenv('BUFFER_MINUTES', 15))
            
            # Add buffer to check range
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            buffer_start = (start_dt - timedelta(minutes=buffer_minutes)).isoformat()
            buffer_end = (end_dt + timedelta(minutes=buffer_minutes)).isoformat()
            
            # Query for existing events
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=buffer_start,
                timeMax=buffer_end,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            conflicts = []
            for event in events:
                if 'dateTime' in event['start']:  # Skip all-day events
                    conflicts.append({
                        'title': event.get('summary', 'No Title'),
                        'start': event['start']['dateTime'],
                        'end': event['end']['dateTime'],
                        'id': event['id']
                    })
            
            return len(conflicts) > 0, conflicts
            
        except HttpError as error:
            return False, [{'error': f"API error: {error}"}]
        except Exception as error:
            return False, [{'error': f"Unexpected error: {error}"}]
    
    def get_upcoming_events(self, days_ahead: int = 7) -> List[Dict]:
        """
        Get upcoming events for the next specified days
        
        Args:
            days_ahead: Number of days to look ahead
        
        Returns:
            List[Dict]: List of upcoming events
        """
        try:
            now = datetime.now(self.timezone)
            end_time = now + timedelta(days=days_ahead)
            
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=now.isoformat(),
                timeMax=end_time.isoformat(),
                maxResults=20,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            upcoming = []
            for event in events:
                if 'dateTime' in event['start']:
                    upcoming.append({
                        'title': event.get('summary', 'No Title'),
                        'start': event['start']['dateTime'],
                        'end': event['end']['dateTime'],
                        'location': event.get('location', ''),
                        'id': event['id']
                    })
            
            return upcoming
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return []
        except Exception as error:
            print(f"Unexpected error: {error}")
            return []
    
    def delete_event(self, event_id: str) -> Tuple[bool, str]:
        """
        Delete an event by ID
        
        Args:
            event_id: Google Calendar event ID
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            return True, "Event deleted successfully"
            
        except HttpError as error:
            return False, f"An error occurred: {error}"
        except Exception as error:
            return False, f"Unexpected error: {error}"
    
    def update_event(self, event_id: str, event_data: Dict) -> Tuple[bool, str]:
        """
        Update an existing event
        
        Args:
            event_id: Google Calendar event ID
            event_data: Updated event information
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Get existing event
            existing_event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            # Update fields
            if 'title' in event_data:
                existing_event['summary'] = event_data['title']
            if 'start_time' in event_data:
                existing_event['start']['dateTime'] = event_data['start_time']
            if 'end_time' in event_data:
                existing_event['end']['dateTime'] = event_data['end_time']
            if 'location' in event_data:
                existing_event['location'] = event_data['location']
            if 'description' in event_data:
                existing_event['description'] = event_data['description']
            
            # Update the event
            updated_event = self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=existing_event
            ).execute()
            
            return True, "Event updated successfully"
            
        except HttpError as error:
            return False, f"An error occurred: {error}"
        except Exception as error:
            return False, f"Unexpected error: {error}"
    
    def find_free_slots(self, date: str, duration_minutes: int, 
                       work_start_hour: int = 9, work_end_hour: int = 18) -> List[Dict]:
        """
        Find free time slots on a given date
        
        Args:
            date: Date in YYYY-MM-DD format
            duration_minutes: Required duration in minutes
            work_start_hour: Start of working hours (24-hour format)
            work_end_hour: End of working hours (24-hour format)
        
        Returns:
            List[Dict]: List of free time slots
        """
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            start_time = self.timezone.localize(
                date_obj.replace(hour=work_start_hour, minute=0, second=0)
            )
            end_time = self.timezone.localize(
                date_obj.replace(hour=work_end_hour, minute=0, second=0)
            )
            
            # Get events for the day
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_time.isoformat(),
                timeMax=end_time.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Find free slots
            free_slots = []
            current_time = start_time
            
            for event in events:
                if 'dateTime' in event['start']:
                    event_start = datetime.fromisoformat(
                        event['start']['dateTime'].replace('Z', '+00:00')
                    )
                    
                    # Check if there's a free slot before this event
                    if (event_start - current_time).total_seconds() >= duration_minutes * 60:
                        free_slots.append({
                            'start': current_time.isoformat(),
                            'end': event_start.isoformat(),
                            'duration_minutes': int((event_start - current_time).total_seconds() / 60)
                        })
                    
                    event_end = datetime.fromisoformat(
                        event['end']['dateTime'].replace('Z', '+00:00')
                    )
                    current_time = max(current_time, event_end)
            
            # Check for free time after last event
            if (end_time - current_time).total_seconds() >= duration_minutes * 60:
                free_slots.append({
                    'start': current_time.isoformat(),
                    'end': end_time.isoformat(),
                    'duration_minutes': int((end_time - current_time).total_seconds() / 60)
                })
            
            return free_slots
            
        except Exception as error:
            print(f"Error finding free slots: {error}")
            return []