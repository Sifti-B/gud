import os
import re
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from yt_dlp import YoutubeDL

app = FastAPI()

# Enable CORS so your frontend can communicate safely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared browser disguise to minimize platform automation blocks
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Path where the uploaded cookies file lives inside the server container
COOKIES_PATH = os.path.join(os.path.dirname(__file__), 'cookies.txt')

class UrlRequest(BaseModel):
    url: str

def safe_name(name: str) -> str:
    """Sanitizes titles by replacing OS-illegal characters with underscores."""
    return re.sub(r'[<>:"/\\|?*]', '_', name)

@app.post("/api/info")
def get_video_info(request: UrlRequest):
    """Endpoint 1: Extracts available video resolutions and data securely."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'http_headers': {'User-Agent': USER_AGENT},
        'nocheckcertificate': True
    }
    
    # Append cookies file dynamically if present in the repository root
    if os.path.exists(COOKIES_PATH):
        ydl_opts['cookiefile'] = COOKIES_PATH

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=False)
            
        if not info:
            raise HTTPException(status_code=400, detail="Could not extract video data.")
            
        formats_list = []
        raw_formats = info.get('formats', []) or []
        
        # Keep track of resolutions we have already added to avoid duplicates
        seen_resolutions = set()
        
        for f in raw_formats:
            vcodec = f.get('vcodec', 'none') or 'none'
            acodec = f.get('acodec', 'none') or 'none'
            format_id = str(f.get('format_id', ''))
            
            # Determine text resolution display string
            height = f.get('height')
            if vcodec == 'none' or not height:
                res_display = "Audio Only"
            else:
                res_display = f"{height}p"
                
            # Create a unique layout label
            ext = str(f.get('ext', 'mp4'))
            note = str(f.get('format_note', '') or '')
            unique_key = f"{res_display}_{ext}"
            
            # Add all audio formats, but filter videos so the dropdown list stays clean
            if res_display == "Audio Only" or unique_key not in seen_resolutions:
                if res_display != "Audio Only":
                    seen_resolutions.add(unique_key)
                    
                formats_list.append({
                    "formatId": format_id or "best",
                    "resolution": res_display,
                    "ext": ext,
                    "note": note
                })
                
        # Safety net backup if raw matrix list parser misses elements
        if not formats_list:
            formats_list.append({
                "formatId": "best",
                "resolution": "Standard / Best Available Quality",
                "ext": "mp4",
                "note": "Default Video Stream"
            })
                
        return {
            "title": str(info.get('title', 'Video')),
            "thumbnail": str(info.get('thumbnail', '')),
            "duration": str(info.get('duration_string', '0:00')),
            "formats": formats_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extractor message: {str(e)}")

@app.get("/api/download")
def download_media(url: str, formatId: str, title: str):
    """Endpoint 2: Downloads requested format and streams it directly to browser."""
    clean_title = safe_name(title or "video")
    output_filename = f"{clean_title}.mp4"
    output_path = os.path.join("/tmp", output_filename) # Use temporary folder

        # Set the video format string option with standard slash fallbacks
    format_selector = f"{formatId}+bestaudio/bestvideo+bestaudio/best"
    
    # If the user selected an option that says 'Audio Only' or custom audio codes
    if formatId == "Audio Only" or "audio" in formatId.lower():
        format_selector = 'bestaudio/best'
        output_filename = f"{clean_title}.mp3"

    ydl_opts = {
        'format': format_selector,
        'merge_output_format': 'mp4',
        'outtmpl': os.path.join("/tmp", f"{clean_title}.%(ext)s"),
        'quiet': True,
        'no_warnings': True,
        'http_headers': {'User-Agent': USER_AGENT},
        'nocheckcertificate': True
    }



    if os.path.exists(COOKIES_PATH):
        ydl_opts['cookiefile'] = COOKIES_PATH

       try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as first_error:
        print(f"Primary format download failed, trying robust safety fallback... Error: {first_error}")
        
        # Step 2: IRONCLAD FALLBACK - Reset parameters and fetch pre-merged absolute best available quality
        ydl_opts['format'] = 'best'
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as fallback_error:
            raise HTTPException(status_code=500, detail=f"Download execution error: {str(fallback_error)}")
            
    # Locate the final processed file in the temporary folder
    actual_file = None
    for ext in ['mp4', 'mkv', 'webm', 'mp3', 'm4a']:
        check_path = os.path.join("/tmp", f"{clean_title}.{ext}")
        if os.path.exists(check_path):
            actual_file = check_path
            output_filename = f"{clean_title}.{ext}"
            break
            
    if not actual_file or not os.path.exists(actual_file):
        raise HTTPException(status_code=500, detail="File processing completed but could not be located on server filesystem.")
        
    # Stream file directly as an attachment to trigger browser download
    return FileResponse(
        path=actual_file, 
        filename=output_filename, 
        media_type="application/octet-stream",
        background=None
    )

# Mount static frontend interface files
app.mount("/", StaticFiles(directory="public", html=True), name="static")
