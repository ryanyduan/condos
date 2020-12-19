from __future__ import print_function
import os
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import httplib2
import oauth2client
from oauth2client import client, tools, file
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from apiclient import errors, discovery
import mimetypes
from email.mime.base import MIMEBase
from datetime import datetime

class Gmail:
    def __init__(self, sender, user_id="me"):
        self.sender = sender
        self.user_id = user_id
        self.file = "condos.csv"
        self.date = datetime.now().strftime("%A %Y-%m-%d")
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
                self.service = build('gmail', 'v1', credentials=creds)

    def create_message_with_attachment(self, recipients, message_text="", error=False, sendAttachment=False):
        subject = "Condo data for {date}".format(date=self.date)
        if error:
            subject = "ERROR scraping condo data for {date}".format(date=self.date)
        message = MIMEMultipart()
        message['to'] = recipients
        message['from'] = self.sender
        message.add_header('Subject', subject)

        if error:
            message_text = "Condo scraping failed with error {error_code}. Error is: {error}".format(error_code=error[0], error=error[1])
        msg = MIMEText(message_text)
        message.attach(msg)

        if sendAttachment:
            content_type, encoding = mimetypes.guess_type(self.file)
            if content_type is None or encoding is not None:
                content_type = 'application/octet-stream'
            main_type, sub_type = content_type.split('/', 1)
            if main_type == 'text':
                with open(self.file, "rb") as f:
                    part = MIMEApplication(
                        f.read(),
                        Name=os.path.basename(self.file)
                    )
                part['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(self.file)
                message.attach(part)
            else:
                fp = open(self.file, 'rb')
                msg = MIMEBase(main_type, sub_type)
                msg.set_payload(fp.read())
                fp.close()
        self.message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
        return self

    def send_message(self):
        try:
            message = (self.service.users().messages().send(userId=self.user_id, body=self.message)
                    .execute())
            return message
        except errors.HttpError as error:
            print('An error occurred: %s' % error)