import datetime
import os.path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request


# If modifying these SCOPES, delete token.json later
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def main():
    creds = None
    # Check if token already exists
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If not, login and save token
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            creds = flow.run_local_server(port=8081)
        # Save for next time
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)

    # Set start and end times
    start_time = datetime.datetime(2025, 7, 25, 15, 0).isoformat()
    end_time = datetime.datetime(2025, 7, 25, 15, 30).isoformat()

    event = {
        'summary': 'Python OAuth Meeting',
        'start': {
            'dateTime': start_time,
            'timeZone': 'Asia/Kolkata',
        },
        'end': {
            'dateTime': end_time,
            'timeZone': 'Asia/Kolkata',
        },
        'conferenceData': {
            'createRequest': {
                'conferenceSolutionKey': {
                    'type': 'hangoutsMeet'
                },
                'requestId': 'oauth-meet-12345'
            }
        },
        'attendees': [
            {'email': 'your-friend@gmail.com'}
        ]
    }

    event_result = service.events().insert(
        calendarId='primary',
        body=event,
        conferenceDataVersion=1
    ).execute()

    print("✅ Meet Created!")
    print("📅 Summary:", event_result['summary'])
    print("🕒 Starts:", event_result['start']['dateTime'])
    print("🔗 Meet Link:", event_result['hangoutLink'])

if __name__ == '__main__':
    main()
