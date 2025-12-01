import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build  # Add this import

SCOPES = ["https://www.googleapis.com/auth/drive"]

class GoogleAuth:
    def __init__(self, credentials_file=None):
        self.creds = None
        self.credentials_file = credentials_file or os.path.join(
            os.path.dirname(__file__), 
            "credentials.json"
        )
        self.token_file = os.path.join(os.path.dirname(__file__), "token.pickle")
        
        # Try to load existing credentials
        self._load_credentials()

    def _load_credentials(self):
        """Load credentials from token file if it exists"""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'rb') as token:
                    self.creds = pickle.load(token)
            except Exception as e:
                print(f"Error loading token: {e}")
                self.creds = None

    def _save_credentials(self):
        """Save credentials to token file"""
        try:
            with open(self.token_file, 'wb') as token:
                pickle.dump(self.creds, token)
        except Exception as e:
            print(f"Error saving token: {e}")

    def login(self):
        """Perform Google OAuth login"""
        if not os.path.exists(self.credentials_file):
            raise FileNotFoundError(f"credentials.json not found at {self.credentials_file}")
        
        flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
        self.creds = flow.run_local_server(port=0)
        
        # Save credentials for future use
        self._save_credentials()

    def is_authenticated(self):
        """Check if user is authenticated with valid credentials"""
        if self.creds is None:
            return False
        
        # Check if credentials are expired and refresh if needed
        if self.creds.expired and self.creds.refresh_token:
            try:
                self.creds.refresh(Request())
                self._save_credentials()
                return True
            except Exception as e:
                print(f"Error refreshing token: {e}")
                return False
        
        return self.creds.valid

    def logout(self):
        """Clear credentials and delete token file"""
        self.creds = None
        if os.path.exists(self.token_file):
            try:
                os.remove(self.token_file)
            except Exception as e:
                print(f"Error removing token file: {e}")

    def get_service(self):
        """Get Google Drive service instance"""
        return build('drive', 'v3', credentials=self.creds)

    def get_user_info(self):
        """Get current user information"""
        try:
            service = build('drive', 'v3', credentials=self.creds)
            about = service.about().get(fields="user").execute()
            return about.get('user', {})
        except Exception as e:
            print(f"Error getting user info: {e}")
            return {}