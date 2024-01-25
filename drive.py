import os.path
import google.auth
import io

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly"]

def get_credentials():
    creds = None
    # The file token.json stores the user"s access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
            "secret_credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=8000)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds

def get_takeout_id(creds):
    try:
        service = build("drive", "v3", credentials=creds)

        # Call the Drive v3 API
        results = (
            service.files()
            .list(pageSize=10, fields="nextPageToken, files(id, name)")
            .execute()
        )

        items = results.get("files", [])
        if not items:
            print("No files found.")
        else:
            print("Files:")
            for item in items:
                if item["name"] == "Takeout":
                    print(f"{item['name']} ({item['id']})")
                    return item["id"]
        return items
    except HttpError as error:
        print(f"An error occurred: {error}")

def get_takeout_files(creds, takeout_id):
    try:
        service = build("drive", "v3", credentials=creds)

        results = (
            service.files()
            .list(
                pageSize=10,
                fields="nextPageToken, files(id, name)",
                q=f"'{takeout_id}' in parents",
            )
            .execute()
        )

        items = results.get("files", [])
        if not items:
            print("No files found.")
        else:
            print("Files:")
            for item in items:
                print(f"{item['name']} ({item['id']})")
                download_file(creds, item["id"])
        return items
    except HttpError as error:
        print(f"An error occurred: {error}")

def download_file(creds, file_id):
    try:
        service = build("drive", "v3", credentials=creds)

        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}%.")

        return fh
    except HttpError as error:
        print(f"An error occurred: {error}")



def main():
    creds = get_credentials()
    takeout_id = get_takeout_id(creds)
    takeout_files = get_takeout_files(creds, takeout_id)

if __name__ == "__main__":
  main()