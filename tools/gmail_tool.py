"""
Gmail API integration for creating and managing email drafts.
"""

import asyncio
import base64
import logging
import os
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from agents.models import EmailDraft, GmailAPIError

logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.drafts',
    'https://www.googleapis.com/auth/gmail.send'
]


class GmailTool:
    """Gmail API client for email operations."""
    
    def __init__(self, credentials_path: str = "./credentials/credentials.json"):
        """
        Initialize Gmail tool.
        
        Args:
            credentials_path: Path to Gmail OAuth2 credentials file
        """
        self.credentials_path = credentials_path
        self.token_path = "./credentials/token.json"
        self.service = None
        self._authenticate()
    
    def _authenticate(self) -> None:
        """Authenticate with Gmail API using OAuth2."""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Gmail credentials refreshed")
                except Exception as e:
                    logger.warning(f"Failed to refresh credentials: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_path):
                    raise GmailAPIError(
                        f"Gmail credentials file not found at {self.credentials_path}. "
                        "Please download credentials.json from Google Cloud Console."
                    )
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    logger.info("Gmail OAuth2 flow completed")
                except Exception as e:
                    raise GmailAPIError(f"OAuth2 authentication failed: {str(e)}")
            
            # Save credentials for future use
            try:
                os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())
                logger.info("Gmail credentials saved")
            except Exception as e:
                logger.warning(f"Failed to save credentials: {e}")
        
        # Build Gmail service
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail service initialized")
        except Exception as e:
            raise GmailAPIError(f"Failed to initialize Gmail service: {str(e)}")
    
    def _create_message(self, email_draft: EmailDraft) -> Dict[str, Any]:
        """
        Create a Gmail message from EmailDraft.
        
        Args:
            email_draft: EmailDraft object
            
        Returns:
            Gmail message dictionary
        """
        # Create MIME message
        if email_draft.attachments:
            message = MIMEMultipart()
        else:
            message = MIMEText(email_draft.body, 'html')
        
        # Set headers
        message['to'] = ', '.join(email_draft.to)
        message['subject'] = email_draft.subject
        
        if email_draft.cc:
            message['cc'] = ', '.join(email_draft.cc)
        if email_draft.bcc:
            message['bcc'] = ', '.join(email_draft.bcc)
        
        # Add body for multipart messages
        if email_draft.attachments:
            body = MIMEText(email_draft.body, 'html')
            message.attach(body)
            
            # TODO: Add attachment handling
            logger.warning("Attachment handling not implemented yet")
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode('utf-8')
        
        return {'raw': raw_message}
    
    async def create_draft(self, email_draft: EmailDraft) -> str:
        """
        Create a Gmail draft.
        
        Args:
            email_draft: EmailDraft object
            
        Returns:
            Draft ID
            
        Raises:
            GmailAPIError: If draft creation fails
        """
        try:
            logger.info(f"Creating Gmail draft: '{email_draft.subject}'")
            
            # Create message
            message = self._create_message(email_draft)
            
            # Create draft
            draft_body = {'message': message}
            draft = self.service.users().drafts().create(
                userId='me', 
                body=draft_body
            ).execute()
            
            draft_id = draft['id']
            logger.info(f"Gmail draft created with ID: {draft_id}")
            
            return draft_id
            
        except HttpError as e:
            error_msg = f"Gmail API error: {e.status_code} - {e.reason}"
            logger.error(error_msg)
            raise GmailAPIError(error_msg, e.status_code)
            
        except Exception as e:
            error_msg = f"Unexpected Gmail error: {str(e)}"
            logger.error(error_msg)
            raise GmailAPIError(error_msg)
    
    async def send_draft(self, draft_id: str) -> str:
        """
        Send a Gmail draft.
        
        Args:
            draft_id: Draft ID to send
            
        Returns:
            Message ID of sent email
            
        Raises:
            GmailAPIError: If sending fails
        """
        try:
            logger.info(f"Sending Gmail draft: {draft_id}")
            
            # Send draft
            sent_message = self.service.users().drafts().send(
                userId='me',
                body={'id': draft_id}
            ).execute()
            
            message_id = sent_message['id']
            logger.info(f"Gmail draft sent with message ID: {message_id}")
            
            return message_id
            
        except HttpError as e:
            error_msg = f"Gmail send error: {e.status_code} - {e.reason}"
            logger.error(error_msg)
            raise GmailAPIError(error_msg, e.status_code)
            
        except Exception as e:
            error_msg = f"Unexpected Gmail send error: {str(e)}"
            logger.error(error_msg)
            raise GmailAPIError(error_msg)
    
    async def get_draft(self, draft_id: str) -> Dict[str, Any]:
        """
        Get draft details.
        
        Args:
            draft_id: Draft ID
            
        Returns:
            Draft information
            
        Raises:
            GmailAPIError: If retrieval fails
        """
        try:
            draft = self.service.users().drafts().get(
                userId='me',
                id=draft_id
            ).execute()
            
            return draft
            
        except HttpError as e:
            error_msg = f"Gmail get draft error: {e.status_code} - {e.reason}"
            logger.error(error_msg)
            raise GmailAPIError(error_msg, e.status_code)
    
    async def list_drafts(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        List Gmail drafts.
        
        Args:
            max_results: Maximum number of drafts to return
            
        Returns:
            List of draft information
            
        Raises:
            GmailAPIError: If listing fails
        """
        try:
            results = self.service.users().drafts().list(
                userId='me',
                maxResults=max_results
            ).execute()
            
            drafts = results.get('drafts', [])
            return drafts
            
        except HttpError as e:
            error_msg = f"Gmail list drafts error: {e.status_code} - {e.reason}"
            logger.error(error_msg)
            raise GmailAPIError(error_msg, e.status_code)


# Convenience functions
async def create_gmail_draft(
    to: List[str],
    subject: str,
    body: str,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    credentials_path: str = "./credentials/credentials.json"
) -> str:
    """
    Create a Gmail draft.
    
    Args:
        to: Recipient email addresses
        subject: Email subject
        body: Email body (HTML supported)
        cc: CC recipients
        bcc: BCC recipients
        credentials_path: Path to Gmail credentials
        
    Returns:
        Draft ID
        
    Raises:
        GmailAPIError: If draft creation fails
    """
    email_draft = EmailDraft(
        to=to,
        subject=subject,
        body=body,
        cc=cc,
        bcc=bcc
    )
    
    gmail_tool = GmailTool(credentials_path)
    return await gmail_tool.create_draft(email_draft)


# Example usage and testing
async def main():
    """Example usage of Gmail tool."""
    try:
        # Create test draft
        draft = EmailDraft(
            to=["test@example.com"],
            subject="Test Email from Research Agent",
            body="""
            <html>
            <body>
            <h2>Research Summary</h2>
            <p>This is a test email generated by the multi-agent research pipeline.</p>
            <p>Best regards,<br>Research Agent</p>
            </body>
            </html>
            """,
            cc=None,
            bcc=None
        )
        
        gmail_tool = GmailTool()
        draft_id = await gmail_tool.create_draft(draft)
        
        print(f"Gmail draft created successfully!")
        print(f"Draft ID: {draft_id}")
        
        # List drafts
        drafts = await gmail_tool.list_drafts(5)
        print(f"\nTotal drafts: {len(drafts)}")
        
    except GmailAPIError as e:
        print(f"Gmail error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main())