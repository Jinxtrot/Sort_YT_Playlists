import os
from flask import Flask, jsonify
import googleapiclient.discovery
import google_auth_oauthlib.flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

app = Flask(__name__)

api_key = os.getenv("API_KEY")
client_secrets_file = os.getenv("CLIENT_SECRET")

api_service_name = "youtube"
api_version = "v3"
scopes = ["https://www.googleapis.com/auth/youtube.readonly"]

def get_credentials():
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, scopes)
    credentials = flow.run_local_server(port=8000, prompt="consent")
    return credentials

def get_playlists(youtube_service):
    response = youtube_service.playlists().list(
        part="snippet,contentDetails",
        mine=True
    ).execute()
    return response["items"]

@app.route('/api/playlists', methods=['GET'])
def api_get_playlists():
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    # Get credentials and create an API client
    credentials = get_credentials()

    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)

    playlists = get_playlists(youtube)
    playlists_data = []

    for playlist in playlists:
        playlist_data = {
            "id": playlist["id"],
            "title": playlist["snippet"]["title"],
            "numberOfVideos": playlist["contentDetails"]["itemCount"]
        }
        playlists_data.append(playlist_data)

    return jsonify(playlists_data)

@app.route('/api/playlist/<playlist_id>', methods=['GET'])
def api_get_playlist(playlist_id):
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    # Get credentials and create an API client
    credentials = get_credentials()

    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)

    response = youtube.playlistItems().list(
        part="snippet,contentDetails",
        playlistId=playlist_id
    ).execute()

    videos = response["items"]
    videos_data = []

    for video in videos:
        video_data = {
            "id": video["contentDetails"]["videoId"],
            "title": video["snippet"]["title"],
            "thumbnail": video["snippet"]["thumbnails"]["default"]["url"]
        }
        videos_data.append(video_data)

    return jsonify(videos_data)

if __name__ == "__main__":
    app.run(debug=True)
