import os
from flask import Flask, jsonify,request
from datetime import date
import googleapiclient.discovery
import google_auth_oauthlib.flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

app = Flask(__name__)

api_key = os.getenv("API_KEY")
client_secrets_file = os.getenv("CLIENT_SECRET")

api_service_name = "youtube"
api_version = "v3"
scopes_read = ["https://www.googleapis.com/auth/youtube.readonly"]
scopes_write = ["https://www.googleapis.com/auth/youtube.force-ssl"]

def get_credentials_read():
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, scopes_read)
    credentials = flow.run_local_server(port=8000, prompt="consent")
    return credentials

def get_credentials_write():
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, scopes_write)
    credentials = flow.run_local_server(port=8000, prompt="consent")
    return credentials

def get_playlists(youtube_service):
    response = youtube_service.playlists().list(
        part="snippet,contentDetails",
        mine=True
    ).execute()
    return response["items"]

@app.route('/api/playlist', methods=['GET'])
def api_get_playlists():
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    # Get credentials and create an API client
    credentials = get_credentials_read()

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
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    credentials = get_credentials_read()

    youtube = googleapiclient.discovery.build(
        "youtube", "v3", credentials=credentials)

    videos_data = {"videos": []}
    next_page_token = None

    while True:
        playlist_response = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            pageToken=next_page_token
        ).execute()

        videos = playlist_response["items"]

        video_ids = [video["contentDetails"]["videoId"] for video in videos]
        videos_response = youtube.videos().list(
            part="snippet,contentDetails",
            id=",".join(video_ids)
        ).execute()

        for video, video_data in zip(videos, videos_response["items"]):
            video_info = {
                "id": video["contentDetails"]["videoId"],
                "title": video["snippet"]["title"],
                "duration": video_data["contentDetails"]["duration"]
            }
            videos_data["videos"].append(video_info)

        if not playlist_response.get("nextPageToken"):
            break
        else:
            next_page_token = playlist_response.get("nextPageToken")

    return jsonify(videos_data)

@app.route('/api/playlist', methods=['POST'])
def api_create_playlist():
    data=request.json
    title=data['title']
    description=date.today().strftime("%B %d, %Y")

    if not title:
        return jsonify({"error": "Missing title"}), 400
    
    credentials = get_credentials_write()

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

    return jsonify(response)

@app.route('/api/playlist/<playlist_id>', methods=['DELETE'])
def api_delete_playlist(playlist_id):
    credentials = get_credentials_write()

    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)

    response = youtube.playlists().delete(
        id=playlist_id
    ).execute()

    return jsonify(response)


if __name__ == "__main__":
    app.run(debug=True)
