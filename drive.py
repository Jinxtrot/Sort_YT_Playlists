import googleapiclient.discovery
import google_auth_oauthlib.flow
import os.path
import isodate
import io
import shutil
import pandas as pd

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from datetime import date

from zipfile import ZipFile

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

api_key = os.getenv("API_KEY")
client_secrets_file = os.getenv("CLIENT_SECRET")

api_service_name = "youtube"
api_version = "v3"
scopes_read = ["https://www.googleapis.com/auth/youtube.readonly"]
scopes_write = ["https://www.googleapis.com/auth/youtube.force-ssl"]

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

current_directory = os.getcwd()

class YoutubeAPI:
    def __init__(self):
        self.api_service_name = "youtube"
        self.api_version = "v3"
        self.scopes_read = ["https://www.googleapis.com/auth/youtube.readonly"]
        self.scopes_write = ["https://www.googleapis.com/auth/youtube.force-ssl"]
        self.credentials = None
        self.youtube = None

    def get_credentials_read(self):
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, self.scopes_read)
        self.credentials = flow.run_local_server(port=8000, prompt="consent")

        return self.credentials

    def get_credentials_write(self):
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, self.scopes_write)
        self.credentials = flow.run_local_server(port=8000, prompt="consent")

        return self.credentials

    def create_playlist(self, playlist_title=None):
        title=playlist_title
        description=date.today().strftime("%B %d, %Y")

        credentials = self.get_credentials_write()
        
        self.youtube = googleapiclient.discovery.build(
            self.api_service_name, self.api_version, credentials=credentials)
        
        request_body = {
            "snippet": {
                "title": title,
                "description": description
            },
            "status": {
                "privacyStatus": "private"
            }
        }

        response = self.youtube.playlists().insert(
            part="snippet,status",
            body=request_body
        ).execute()

        new_playlist_id=response["id"]

        return new_playlist_id
    
    def insert_videos_in_playlist(self, name, videos_id):
        new_playlist_id=self.create_playlist(playlist_title=name)
        
        for video in videos_id:
            try:
                request_body = {
                    "snippet": {
                        "playlistId": new_playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video
                        }
                    }
                }

                response = self.youtube.playlistItems().insert(
                    part="snippet",
                    body=request_body
                ).execute()
            except googleapiclient.errors.HttpError as e:
                print(f"HTTP Error: {e.resp.status} - {e.content}")

        return response


def get_credentials():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
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
                download_file(creds, item["id"], "/Users/eduardo/projects/personal-projects/YT_API/takeout")
        return items
    except HttpError as error:
        print(f"An error occurred: {error}")

def download_file(creds, file_id, destination_folder):
    try:
        service = build("drive", "v3", credentials=creds)

        request = service.files().get_media(fileId=file_id)

        fh = io.FileIO(current_directory + "/takeout.zip", 'wb')  # Specify the destination folder and filename

        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}%.")
        
        print(f"File downloaded to: {destination_folder}/{file_id}")

        return fh
    except HttpError as error:
        print(f"An error occurred: {error}")

def delete_file(file_path):
    os.remove(file_path)
    print(f"File {file_path} deleted")

def move_file(file_path, destination_folder):
    os.rename(file_path, destination_folder)
    print(f"File {file_path} moved to {destination_folder}")

def delete_folder(folder_path):
    shutil.rmtree(folder_path)
    print(f"Folder {folder_path} deleted")

def extract_zip_file(file_path):
    with ZipFile(file_path, "r") as zip:
        zip.printdir()
        print("Extracting all the files now...")
        zip.extractall(current_directory)
        print("Done!")
    delete_file(current_directory + "/takeout.zip")
    move_file(current_directory + "/Takeout/YouTube and YouTube Music/playlists/Watch later-videos.csv", current_directory+"/watch_later.csv")
    delete_folder(current_directory + "/Takeout")

def extract_videos_id(file_path):
    videos_df=pd.read_csv(file_path)
    videos_id = videos_df["Video ID"].tolist()
    return videos_id

def get_credentials_write_YT():
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, scopes_write)
    credentials = flow.run_local_server(port=8000, prompt="consent")
    return credentials

def get_credentials_read_YT():
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, scopes_read)
    credentials = flow.run_local_server(port=8000, prompt="consent")
    return credentials

def api_create_playlist(playlist_title=None):
    title=playlist_title
    description=date.today().strftime("%B %d, %Y")
    
    credentials = get_credentials_write_YT()

    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)
    
    request_body = {
        "snippet": {
            "title": title,
            "description": description
        },
        "status": {
            "privacyStatus": "private"
        }
    }

    response = youtube.playlists().insert(
        part="snippet,status",
        body=request_body
    ).execute()

    return response,youtube

def insert_videos_in_playlist(name,videos_id):
    response_creation,youtube=api_create_playlist(playlist_title=name)

    new_playlist_id=response_creation["id"]
    
    for video in videos_id:
        try:
            request_body = {
                "snippet": {
                    "playlistId": new_playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video
                    }
                }
            }

            response = youtube.playlistItems().insert(
                part="snippet",
                body=request_body
            ).execute()
    # Your API request here
        except googleapiclient.errors.HttpError as e:
            print(f"HTTP Error: {e.resp.status} - {e.content}")

    return response

def sort_videos_length(video_ids):
    creds = get_credentials_read_YT()

    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, credentials=creds)
    durations = []
    for video_id in video_ids:
        try:
            request = youtube.videos().list(
                part="contentDetails",
                id=video_id
            )
            response = request.execute()
            data = response

            for item in data["items"]:
                duration = isodate.parse_duration(item["contentDetails"]["duration"])
                durations.append((item["id"], duration.total_seconds()))
        except googleapiclient.errors.HttpError as e:
            print(f"HTTP Error: {e.resp.status} - {e.content}")

    durations.sort(key=lambda x: x[1])
    durations = [video_id for video_id, _ in durations]

    return durations

def main():
    # creds = get_credentials()
    # takeout_id = get_takeout_id(creds)
    # get_takeout_files(creds, takeout_id)
    # extract_zip_file(current_directory + "/takeout.zip")
    videos_id = extract_videos_id(current_directory+"/watch_later.csv")
    videos_id_sorted=sort_videos_length(videos_id)

    youtube = YoutubeAPI()
    youtube.get_credentials_write()
    youtube.insert_videos_in_playlist("Watch Later - Sorted",videos_id_sorted)

    
    # print(videos_id_sorted)
    # insert_videos_in_playlist("Watch Later - Sorted",videos_id_sorted)

if __name__ == "__main__":
  main()