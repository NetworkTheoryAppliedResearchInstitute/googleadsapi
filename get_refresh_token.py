"""
Generate a Google Ads OAuth2 refresh token.

Set CLIENT_ID and CLIENT_SECRET in your environment (or .env file) before running:

    export CLIENT_ID=your-client-id.apps.googleusercontent.com
    export CLIENT_SECRET=your-client-secret

Then run:
    python get_refresh_token.py
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

load_dotenv()

client_id     = os.environ["CLIENT_ID"]
client_secret = os.environ["CLIENT_SECRET"]

flow = InstalledAppFlow.from_client_config(
    {"installed": {
        "client_id":     client_id,
        "client_secret": client_secret,
        "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
        "token_uri":     "https://accounts.google.com/o/oauth2/token",
    }},
    scopes=["https://www.googleapis.com/auth/adwords"],
)

creds = flow.run_local_server(port=0)
print("\nREFRESH TOKEN:", creds.refresh_token)
print("Copy this value into google-ads.yaml as 'refresh_token'.")
