"""
Step 4: Upload to YouTube using FREE YouTube Data API v3
Setup guide: https://developers.google.com/youtube/v3/quickstart/python
Install: pip install google-auth-oauthlib google-api-python-client
"""

import os
import logging
import pickle
from typing import Optional, List

log = logging.getLogger(__name__)

# ─── CONFIG ──────────────────────────────────────────────────────
# Path to your OAuth2 credentials JSON (downloaded from Google Cloud Console)
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_PICKLE_FILE   = "youtube_token.pickle"

# YouTube category IDs (pick one for your content)
CATEGORIES = {
    "film":          1,
    "autos":         2,
    "music":        10,
    "pets":         15,
    "sports":       17,
    "gaming":       20,
    "comedy":       23,
    "entertainment":24,
    "news":         25,
    "how_to":       26,
    "education":    27,
    "science":      28,
    "travel":       19,
}
DEFAULT_CATEGORY = CATEGORIES["education"]  # ← Change this for your niche

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


def reauthenticate():
    """
    Re-authenticate with full YouTube scope (needed for thumbnail upload).
    Run this locally, then update YOUTUBE_TOKEN_B64 in GitHub secrets.
    """
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not os.path.exists(CLIENT_SECRETS_FILE):
        log.error(f"Missing {CLIENT_SECRETS_FILE}")
        return False

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    credentials = flow.run_local_server(port=0)

    with open(TOKEN_PICKLE_FILE, "wb") as f:
        pickle.dump(credentials, f)

    log.info(f"Re-authenticated! Token saved to {TOKEN_PICKLE_FILE}")
    log.info("Now update YOUTUBE_TOKEN_B64 in GitHub secrets:")
    log.info(f"  base64 -w 0 {TOKEN_PICKLE_FILE}")
    return True


def get_authenticated_service():
    """Authenticate and return YouTube API service."""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        log.error("Google API libraries not installed. Run:\n"
                  "pip install google-auth-oauthlib google-api-python-client")
        return None

    credentials = None

    # Load saved token if it exists
    if os.path.exists(TOKEN_PICKLE_FILE):
        with open(TOKEN_PICKLE_FILE, "rb") as f:
            credentials = pickle.load(f)

    # Refresh or re-authenticate
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            from google.auth.transport.requests import Request
            credentials.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                log.error(
                    f"Missing {CLIENT_SECRETS_FILE}!\n"
                    "1. Go to https://console.cloud.google.com\n"
                    "2. Create a project → Enable YouTube Data API v3\n"
                    "3. Create OAuth 2.0 credentials → Download as client_secrets.json\n"
                    "4. Place client_secrets.json in the project folder"
                )
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            credentials = flow.run_local_server(port=0)

        # Save token for next time (so you don't need to re-login)
        with open(TOKEN_PICKLE_FILE, "wb") as f:
            pickle.dump(credentials, f)
        log.info("Saved YouTube credentials for future runs")

    service = build("youtube", "v3", credentials=credentials)
    log.info("YouTube API authenticated successfully")
    return service


def upload_to_youtube(
    video_path: str,
    title: str,
    description: str,
    tags: List[str],
    thumbnail_path: str = None,
    privacy: str = "public",     # "public", "private", or "unlisted"
    category_id: int = DEFAULT_CATEGORY,
) -> Optional[str]:
    """
    Upload a video to YouTube.

    Args:
        video_path:      Path to the MP4 file
        title:           Video title
        description:     Video description
        tags:            List of tag strings
        thumbnail_path:  Optional path to thumbnail image
        privacy:         "public", "private", or "unlisted"
        category_id:     YouTube category ID
    Returns:
        YouTube video ID string if successful, None on failure
    """
    try:
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        log.error("google-api-python-client not installed. Run: pip install google-api-python-client")
        return None

    if not os.path.exists(video_path):
        log.error(f"Video file not found: {video_path}")
        return None

    service = get_authenticated_service()
    if not service:
        return None

    body = {
        "snippet": {
            "title":       title[:100],    # YouTube max is 100 chars
            "description": description,
            "tags":        tags[:500],     # YouTube max 500 tags
            "categoryId":  str(category_id),
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus":          privacy,
            "selfDeclaredMadeForKids": False,
        }
    }

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024  # 1MB chunks
    )

    log.info(f"Uploading '{title}' ({privacy})...")

    try:
        request = service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                log.info(f"Upload progress: {pct}%")

        video_id = response.get("id")
        log.info(f"Upload complete! Video ID: {video_id}")

        # Set thumbnail if provided
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                service.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path)
                ).execute()
                log.info("Thumbnail uploaded successfully")
            except Exception as e:
                log.warning(f"Thumbnail upload failed (video still uploaded): {e}")

        return video_id

    except Exception as e:
        log.error(f"YouTube upload failed: {e}")
        return None


if __name__ == "__main__":
    print("YouTube upload module loaded successfully.")
    print("To use: call upload_to_youtube() from main.py")
    print(f"Looking for credentials at: {CLIENT_SECRETS_FILE}")
