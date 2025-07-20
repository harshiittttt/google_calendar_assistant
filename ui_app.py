import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from calendar_api import GoogleCalendarAPI
from grok_nlp import GrokNLP
import json

# Page configuration
st.set_page_config(
    page_title="AI Calendar Assistant",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    font-weight: bold;
    color: #1f77b4;
    text-align: center;
    margin-bottom: 2rem;
}

.event-card {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 10px;
    margin: 0.5rem 0;
    border-left: 4px solid #1f77b4;
}

.conflict-card {
    background-color: #ffe6e6;
    padding: 1rem;
    border-radius: 10px;
    margin: 0.5rem 0;
    border-left: 4px solid #ff4444;
}

.success-card {
    background-color: #e6ffe6;
    padding: 1rem;
    border-radius: 10px;
    margin: 0.5rem 0;
    border-left: 4px solid #44ff44;
}

.sidebar-section {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 10px;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'calendar_api' not in st.session_state:
    try:
        st.session_state.calendar_api = GoogleCalendarAPI()
        st.session_state.grok_nlp = GrokNLP()
        st.session_state.authenticated = True
    except Exception as e:
        st.session_state.authenticated = False
        st.session_state.error_message = str(e)

if 'events_created' not in st.session_state:
    st.session_state.events_created = []

if 'last_extraction' not in st.session_state:
    st.session_state.last_extraction = None

def main():
    st.markdown('<h1 class="main-header">🤖 AI Calendar Assistant</h1>', unsafe_allow_html=True)
    
    if not st.session_state.get('authenticated', False):
        st.error(f"❌ Authentication failed: {st.session_state.get('error_message', 'Unknown error')}")
        st.info("Please check your credentials.json file and Grok API key in .env file")
        return
    
    # Sidebar
    with st.sidebar:
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.header("📋 Quick Actions")
        
        if st.button("🔄 Refresh Calendar"):
            st.cache_data.clear()
            st.rerun()
        
        if st.button("📊 View Upcoming Events"):
            st.session_state.show_upcoming = True
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Settings
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.header("⚙️ Settings")
        
        st.session_state.default_duration = st.slider(
            "Default Event Duration (minutes)", 
            min_value=15, 
            max_value=240, 
            value=60, 
            step=15
        )
        
        st.session_state.buffer_time = st.slider(
            "Buffer Time Between Events (minutes)",
            min_value=0,
            max_value=60,
            value=15,
            step=5
        )
        
        st.session_state.work_start = st.time_input(
            "Work Day Start", 
            value=datetime.strptime("09:00", "%H:%M").time()
        )
        
        st.session_state.work_end = st.time_input(
            "Work Day End", 
            value=datetime.strptime("18:00", "%H:%M").time()
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📝 Schedule New Event")
        
        # Text input for natural language
        user_input = st.text_area(
            "What would you like to schedule?",
            placeholder="Examples:\n• Team meeting tomorrow at 2 PM for 1 hour\n• Lunch with Sarah on Friday at 12:30 PM at McDonald's\n• Doctor appointment next Monday from 10 AM to 10:30 AM\n• Call with client this Thursday at 3 PM",
            height=100,
            help="Describe your event in natural language. Include time, date, duration, and location if applicable."
        )
        
        # Action buttons
        col_extract, col_schedule, col_clear = st.columns(3)
        
        with col_extract:
            extract_btn = st.button("🔍 Extract Info", type="secondary", use_container_width=True)
        
        with col_schedule:
            schedule_btn = st.button("📅 Schedule Event", type="primary", use_container_width=True)
        
        with col_clear:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.last_extraction = None
                st.rerun()
        
        # Extract information
        if extract_btn and user_input.strip():
            with st.spinner("🤖 Extracting event information..."):
                success, result = st.session_state.grok_nlp.extract_event_info(user_input)
                
                if success:
                    st.session_state.last_extraction = result
                    st.success("✅ Event information extracted successfully!")
                else:
                    st.error(f"❌ Failed to extract information: {result.get('error', 'Unknown error')}")
        
        # Display extracted information
        if st.session_state.last_extraction:
            st.subheader("📋 Extracted Event Information")
            
            with st.container():
                st.markdown('<div class="event-card">', unsafe_allow_html=True)
                
                col_info1, col_info2 = st.columns(2)
                
                with col_info1:
                    st.write(f"**Title:** {st.session_state.last_extraction['title']}")
                    st.write(f"**Start:** {format_datetime(st.session_state.last_extraction['start_time'])}")
                    st.write(f"**End:** {format_datetime(st.session_state.last_extraction['end_time'])}")
                
                with col_info2:
                    st.write(f"**Duration:** {st.session_state.last_extraction['duration_minutes']} minutes")
                    st.write(f"**Location:** {st.session_state.last_extraction.get('location', 'Not specified')}")
                    st.write(f"**Category:** {st.session_state.last_extraction.get('category', 'Other')}")
                
                if st.session_state.last_extraction.get('description'):
                    st.write(f"**Description:** {st.session_state.last_extraction['description']}")
                
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Schedule event
        if schedule_btn and st.session_state.last_extraction:
            schedule_event(st.session_state.last_extraction)
        elif schedule_btn and not st.session_state.last_extraction:
            st.warning("⚠️ Please extract event information first!")
        
        # Show recent events created
        if st.session_state.events_created:
            st.subheader("✅ Recently Created Events")
            for event in st.session_state.events_created[-3:]:  # Show last 3
                st.markdown('<div class="success-card">', unsafe_allow_html=True)
                st.write(f"**{event['title']}** - {format_datetime(event['start_time'])}")
                st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.header("📅 Calendar Overview")
        
        # Show upcoming events
        show_upcoming_events()
        
        # Quick scheduling options
        st.subheader("⚡ Quick Schedule")
        
        quick_options = [
            "15 minute break in 1 hour",
            "Lunch break at 1 PM today",
            "Team standup tomorrow at 9 AM",
            "1 hour focus time this afternoon"
        ]
        
        selected_quick = st.selectbox("Choose a quick option:", ["Select..."] + quick_options)
        
        if selected_quick != "Select...":
            if st.button(f"Schedule: {selected_quick}", use_container_width=True):
                with st.spinner("Processing..."):
                    success, result = st.session_state.grok_nlp.extract_event_info(selected_quick)
                    if success:
                        schedule_event(result)
                    else:
                        st.error(f"Failed to process: {result.get('error')}")

def schedule_event(event_data):
    """Schedule an event with conflict checking"""
    
    with st.spinner("🔍 Checking for conflicts..."):
        # Check for conflicts
        has_conflicts, conflicts = st.session_state.calendar_api.check_conflicts(
            event_data['start_time'],
            event_data['end_time'],
            st.session_state.get('buffer_time', 15)
        )
    
    if has_conflicts:
        st.error("⚠️ Scheduling Conflict Detected!")
        
        # Show conflicts
        st.subheader("🚨 Conflicting Events:")
        for conflict in conflicts:
            if 'error' not in conflict:
                st.markdown('<div class="conflict-card">', unsafe_allow_html=True)
                st.write(f"**{conflict['title']}**")
                st.write(f"Time: {format_datetime(conflict['start'])} - {format_datetime(conflict['end'])}")
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Suggest alternatives
        st.subheader("💡 Suggested Alternatives:")
        
        col_suggest, col_force = st.columns(2)
        
        with col_suggest:
            if st.button("🔄 Get Suggestions", use_container_width=True):
                get_suggestions(event_data, conflicts)
        
        with col_force:
            if st.button("⚠️ Schedule Anyway", type="secondary", use_container_width=True):
                force_schedule_event(event_data)
    
    else:
        # No conflicts, proceed with scheduling
        with st.spinner("📅 Creating calendar event..."):
            success, result = st.session_state.calendar_api.create_event(event_data)
        
        if success:
            st.success("🎉 Event scheduled successfully!")
            st.balloons()
            
            # Add to recent events
            event_data['event_id'] = result
            st.session_state.events_created.append(event_data)
            
            # Clear the extraction
            st.session_state.last_extraction = None
            
            # Auto-refresh upcoming events
            st.cache_data.clear()
            
        else:
            st.error(f"❌ Failed to create event: {result}")

def get_suggestions(original_event, conflicts):
    """Get alternative time suggestions"""
    
    with st.spinner("🤖 Finding alternative times..."):
        # Get suggestions from Grok
        success, suggestions = st.session_state.grok_nlp.suggest_alternatives(
            f"Schedule {original_event['title']} for {original_event['duration_minutes']} minutes",
            conflicts
        )
        
        if success and suggestions:
            st.write("📋 **Alternative Times:**")
            
            for i, suggestion in enumerate(suggestions[:3]):  # Show top 3
                col_suggestion, col_book = st.columns([3, 1])
                
                with col_suggestion:
                    st.markdown('<div class="event-card">', unsafe_allow_html=True)
                    st.write(f"**Option {i+1}:** {suggestion['suggestion']}")
                    st.write(f"Time: {format_datetime(suggestion['start_time'])} - {format_datetime(suggestion['end_time'])}")
                    st.write(f"Reason: {suggestion['reason']}")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col_book:
                    if st.button(f"Book #{i+1}", key=f"book_{i}", use_container_width=True):
                        # Update event data with new time
                        updated_event = original_event.copy()
                        updated_event['start_time'] = suggestion['start_time']
                        updated_event['end_time'] = suggestion['end_time']
                        
                        # Recalculate duration
                        start_dt = datetime.fromisoformat(suggestion['start_time'])
                        end_dt = datetime.fromisoformat(suggestion['end_time'])
                        updated_event['duration_minutes'] = int((end_dt - start_dt).total_seconds() / 60)
                        
                        # Schedule the updated event
                        schedule_event(updated_event)
                        break
        else:
            st.warning("Unable to generate suggestions. Try manually adjusting the time.")
            
            # Show free slots as backup
            show_free_slots(original_event)

def show_free_slots(event_data):
    """Show available free slots"""
    
    try:
        start_date = datetime.fromisoformat(event_data['start_time']).strftime('%Y-%m-%d')
        
        free_slots = st.session_state.calendar_api.find_free_slots(
            start_date,
            event_data['duration_minutes'],
            st.session_state.work_start.hour,
            st.session_state.work_end.hour
        )
        
        if free_slots:
            st.write("🕐 **Available Time Slots:**")
            
            for i, slot in enumerate(free_slots[:5]):  # Show top 5
                col_slot, col_use = st.columns([3, 1])
                
                with col_slot:
                    st.write(f"**Slot {i+1}:** {format_datetime(slot['start'])} - {format_datetime(slot['end'])} ({slot['duration_minutes']} min available)")
                
                with col_use:
                    if st.button(f"Use Slot {i+1}", key=f"slot_{i}", use_container_width=True):
                        # Update event to use this slot
                        updated_event = event_data.copy()
                        slot_start = datetime.fromisoformat(slot['start'])
                        slot_end = slot_start + timedelta(minutes=event_data['duration_minutes'])
                        
                        updated_event['start_time'] = slot_start.strftime('%Y-%m-%dT%H:%M:%S')
                        updated_event['end_time'] = slot_end.strftime('%Y-%m-%dT%H:%M:%S')
                        
                        schedule_event(updated_event)
                        break
        else:
            st.info("No suitable free slots found for today. Try a different day.")
            
    except Exception as e:
        st.error(f"Error finding free slots: {e}")

def force_schedule_event(event_data):
    """Force schedule event despite conflicts"""
    
    st.warning("⚠️ Scheduling event despite conflicts...")
    
    with st.spinner("📅 Creating calendar event..."):
        success, result = st.session_state.calendar_api.create_event(event_data)
    
    if success:
        st.success("✅ Event scheduled (with conflicts noted)")
        event_data['event_id'] = result
        st.session_state.events_created.append(event_data)
        st.session_state.last_extraction = None
        st.cache_data.clear()
    else:
        st.error(f"❌ Failed to create event: {result}")

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_upcoming_events():
    """Get upcoming events (cached)"""
    return st.session_state.calendar_api.get_upcoming_events(days_ahead=7)

def show_upcoming_events():
    """Display upcoming events"""
    
    upcoming_events = get_upcoming_events()
    
    if upcoming_events:
        st.write(f"📋 **Next {len(upcoming_events)} Events:**")
        
        for event in upcoming_events[:5]:  # Show next 5
            st.markdown('<div class="event-card">', unsafe_allow_html=True)
            
            # Parse datetime for display
            start_dt = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(event['end'].replace('Z', '+00:00'))
            
            # Calculate time until event
            now = datetime.now(pytz.timezone('Asia/Kolkata'))
            time_until = start_dt.replace(tzinfo=pytz.timezone('Asia/Kolkata')) - now
            
            if time_until.total_seconds() > 0:
                if time_until.days > 0:
                    time_str = f"in {time_until.days} days"
                elif time_until.seconds > 3600:
                    hours = time_until.seconds // 3600
                    time_str = f"in {hours} hours"
                else:
                    minutes = time_until.seconds // 60
                    time_str = f"in {minutes} minutes"
            else:
                time_str = "ongoing/past"
            
            st.write(f"**{event['title']}**")
            st.write(f"🕐 {format_datetime(event['start'])}")
            st.write(f"⏰ {time_str}")
            
            if event['location']:
                st.write(f"📍 {event['location']}")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    else:
        st.info("No upcoming events found.")

def format_datetime(dt_string):
    """Format datetime string for display"""
    try:
        dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        return dt.strftime('%a, %b %d at %I:%M %p')
    except:
        return dt_string

if __name__ == "__main__":
    main()