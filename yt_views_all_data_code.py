# Step 1: Install required libraries
!pip install --upgrade google-api-python-client gspread oauth2client

# Step 2: Authenticate Google Sheets access
from google.colab import auth
auth.authenticate_user()

import gspread
from oauth2client.client import GoogleCredentials

gc = gspread.authorize(GoogleCredentials.get_application_default())

# Step 1: Install required libraries
!pip install --upgrade google-api-python-client gspread oauth2client

# Authenticate with Google Sheets
import google.auth
from google.colab import auth
import gspread

auth.authenticate_user()
creds, _ = google.auth.default()
gc = gspread.authorize(creds)

from googleapiclient.discovery import build
import datetime
import re

# 🔑 Replace with your YouTube API key
YOUTUBE_API_KEY = 'your YouTube API key'  # Replace this!

youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# Get current UTC time with timezone
today = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
two_months_ago = today - datetime.timedelta(days=60)

def extract_channel_id(channel_input):
    if "youtube.com/channel/" in channel_input:
        return channel_input.split("/channel/")[1].split("/")[0]

    match = re.search(r"@[\w\d_.-]+", channel_input)
    if match:
        handle = match.group()
        try:
            res = youtube.search().list(
                q=handle.replace("@", ""),
                type='channel',
                part='snippet',
                maxResults=1
            ).execute()
            return res['items'][0]['snippet']['channelId']
        except:
            return None

    return channel_input

def get_recent_video_ids(channel_id):
    res = youtube.channels().list(
        part='contentDetails',
        id=channel_id
    ).execute()
    playlist_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    video_ids = []
    next_page_token = None
    while True:
        res = youtube.playlistItems().list(
            part='snippet',
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        ).execute()

        for item in res['items']:
            published_at = item['snippet']['publishedAt']
            published_dt = datetime.datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            if published_dt >= two_months_ago:
                video_ids.append(item['snippet']['resourceId']['videoId'])

        next_page_token = res.get('nextPageToken')
        if not next_page_token:
            break

    return video_ids

def get_video_metadata(video_ids):
    all_data = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        res = youtube.videos().list(
            part='snippet,statistics,contentDetails,status',
            id=','.join(batch)
        ).execute()

        for item in res['items']:
            snippet = item['snippet']
            stats = item.get('statistics', {})
            content = item.get('contentDetails', {})
            status = item.get('status', {})

            data = {
                "Title": snippet.get("title", ""),
                "Published Date": snippet.get("publishedAt", "").split("T")[0],
                "Views": stats.get("viewCount", 0),
                "Likes": stats.get("likeCount", 0),
                "Comments": stats.get("commentCount", 0),
                "Duration": content.get("duration", ""),
                "Description": snippet.get("description", ""),
                "Tags": ', '.join(snippet.get("tags", [])),
                "Thumbnail URL": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                "Video URL": f"https://www.youtube.com/watch?v={item['id']}",
                "Privacy": status.get("privacyStatus", ""),
                "Made for Kids": status.get("madeForKids", ""),
                "License": status.get("license", ""),
                "Category ID": snippet.get("categoryId", "")
            }
            all_data.append(data)
    return all_data

# Replace with any one channel input (handle, link, or ID)
channel_input = "https://www.youtube.com/@SandeepSeminars"

channel_id = extract_channel_id(channel_input)
if not channel_id:
    print("❌ Failed to get channel ID.")
else:
    video_ids = get_recent_video_ids(channel_id)
    if not video_ids:
        print("❌ No videos found in last 2 months.")
    else:
        video_data = get_video_metadata(video_ids)

        # Create and update Google Sheet
        sheet_name = f"YouTube Full Report - {channel_input.strip('@').split('/')[-1]}"
        sheet = gc.create(sheet_name)
        worksheet = sheet.get_worksheet(0)

        headers = list(video_data[0].keys())
        rows = [list(v.values()) for v in video_data]

        worksheet.update([headers] + rows)
        print("✅ Full data saved to Google Sheet:", sheet.url)
