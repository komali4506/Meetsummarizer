# 📅 Google Meet Link Creator with Python

This Python script creates a Google Calendar event with an auto-generated **Google Meet link**, using the Google Calendar API and OAuth2 authentication.

## ✅ Features

- Authenticate with Google via OAuth2
- Create a calendar event with:
  - Title
  - Start and End time
  - Attendee email(s)
  - Google Meet conferencing link
- Automatically saves and reuses token credentials (`token.json`)

## 🛠️ Requirements

Make sure Python 3.7+ is installed.

Install the required libraries:

```bash
pip install --upgrade google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
