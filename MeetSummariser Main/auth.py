import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scopes required for Google Calendar and Meet
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def authenticate_google():
    """
    Authenticate with Google and create a proper token.json file
    """
    creds = None
    
    # Delete existing token.json if it exists (to force re-authentication)
    if os.path.exists('token.json'):
        print("🗑️ Removing existing token.json to force re-authentication...")
        os.remove('token.json')
    
    # Check if credentials file exists
    if not os.path.exists('client_secret.json'):
        print("❌ Error: client_secret.json not found!")
        print("Please make sure you have downloaded your OAuth credentials from Google Cloud Console")
        print("and saved them as 'client_secret.json' in this directory.")
        return False
    
    print("🔐 Starting Google OAuth authentication...")
    print("This will open a browser window for authentication.")
    
    # Run OAuth flow
    flow = InstalledAppFlow.from_client_secrets_file(
        'client_secret.json', 
        SCOPES,
        redirect_uri='http://localhost:8080'  # Ensure this matches your OAuth settings
    )
    
    # This will open browser and prompt for authentication
    creds = flow.run_local_server(
        port=8080,
        access_type='offline',  # This ensures we get a refresh token
        prompt='consent'        # This forces consent screen to appear
    )
    
    # Save the credentials for future use
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    
    print("✅ Authentication successful!")
    print("📄 token.json created with proper refresh_token")
    
    # Test the credentials by making a simple API call
    try:
        service = build('calendar', 'v3', credentials=creds)
        calendar_list = service.calendarList().list().execute()
        print(f"🔍 Found {len(calendar_list.get('items', []))} calendars in your account")
        print("✅ Google Calendar API access confirmed!")
        return True
    except Exception as e:
        print(f"❌ Error testing API access: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Google Meet Recorder - Authentication Setup")
    print("=" * 50)
    
    success = authenticate_google()
    
    if success:
        print("\n🎉 Setup complete! You can now run your main application:")
        print("   python app.py")
    else:
        print("\n❌ Authentication failed. Please check your setup and try again.")
    
    input("\nPress Enter to exit...")