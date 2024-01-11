import os
from flask import Flask, jsonify,request
from datetime import date
import googleapiclient.discovery
import google_auth_oauthlib.flow

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
    

def sort_videos_length(videos):
    for video in videos:
        duration_str = video["duration"].replace('PT', '')
    
        has_hours = 'H' in duration_str
        has_minutes = 'M' in duration_str
        has_seconds = 'S' in duration_str

        hours, minutes, seconds = 0, 0, 0

        if has_hours:
            temp=duration_str.split('H')
            duration_str=temp[1]
            hours=int(temp[0])
        if has_minutes:
            temp=duration_str.split('M')
            duration_str=temp[1]
            minutes=int(temp[0])
        if has_seconds:
            temp=duration_str.split('S')
            seconds=int(temp[0])

        total_seconds = hours * 3600 + minutes * 60 + seconds
        video["duration"] = total_seconds

    return sorted(videos, key=lambda video: video["duration"])

@app.route('/api/playlist', methods=['GET'])
def api_get_playlists():
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

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

    playlist_name=youtube.playlists().list(part="snippet",id=playlist_id).execute().get("items")[0].get("snippet").get("title")

    videos_data={"id":playlist_id,"playlist_name":playlist_name,"videos":videos_data["videos"]}
    videos_data["videos"] = sort_videos_length(videos_data["videos"])

    return jsonify(videos_data)

def api_create_playlist(playlist_title=None):
    title=playlist_title
    description=date.today().strftime("%B %d, %Y")
    
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

    return jsonify(response),youtube

@app.route('/api/playlist/sort/<playlist_id>', methods=['POST'])
def insert_videos_in_playlist(playlist_id):

    videos=api_get_playlist(playlist_id)
    response_videos=videos.get_json()

    playlist_title=response_videos.get("playlist_name","")+" - Sorted"

    response_creation,youtube=api_create_playlist(playlist_title)

    response_creation=response_creation.get_json()
    new_playlist_id=response_creation["id"]
    
    for video in response_videos["videos"]:
        try:
            request_body = {
                "snippet": {
                    "playlistId": new_playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video["id"]
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
