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

class UrlRequest(BaseModel):
    url: str

def safe_name(name: str) -> str:
    """Sanitizes titles by replacing OS-illegal characters with underscores."""
    return re.sub(r'[<>:"/\\|?*]', '_', name)

@app.post("/api/info")
def get_video_info(request: UrlRequest):
    """Endpoint 1: Extracts available video resolutions and data."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'http_headers': {'User-Agent': USER_AGENT},
        'nocheckcertificate': True,
        'cookiefile': 'cookies.txt'
    }

    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=False)
            
        if not info or 'formats' not in info:
            raise HTTPException(status_code=400, detail="Could not extract video formats.")
            
        # Parse available resolutions cleanly
        formats_list = []
        for f in info['formats']:
            if f.get('vcodec') != 'none' or f.get('acodec') != 'none':
                # Determine resolution display string
                res = f.get('resolution') or f"{f.get('width','?')}x{f.get('height','?')}"
                if f.get('vcodec') == 'none':
                    res = "Audio Only"
                    
                formats_list.append({
                    "formatId": f.get('format_id'),
                    "resolution": res,
                    "ext": f.get('ext', 'mp4'),
                    "note": f.get('format_note', '')
                })
                
        return {
            "title": info.get('title', 'Video'),
            "thumbnail": info.get('thumbnail', ''),
            "duration": info.get('duration_string', '0:00'),
            "formats": formats_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch metadata: {str(e)}")

@app.get("/api/download")
def download_media(url: str, formatId: str, title: str):
    """Endpoint 2: Downloads requested format and streams it directly to browser."""
    clean_title = safe_name(title or "video")
    output_filename = f"{clean_title}.mp4"
    output_path = os.path.join("/tmp", output_filename) # Use temporary folder

    ydl_opts = {
        'format': f"{formatId}+bestaudio/best" if formatId != "best" else "bestvideo+bestaudio/best",
        'merge_output_format': 'mp4',
        'outtmpl': os.path.join("/tmp", f"{clean_title}.%(ext)s"),
        'quiet': True,
        'no_warnings': True,
        'http_headers': {'User-Agent': USER_AGENT},
        'nocheckcertificate': True,
        'cookiefile': 'cookies.txt'
    }


    try:
        # Download file to temporary directory
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        if not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="File processing failed on server.")
            
        # Stream file directly as an attachment to trigger browser download
        return FileResponse(
            path=output_path, 
            filename=output_filename, 
            media_type="video/mp4",
            background=None # File can be safely cleaned up later or handled automatically
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download execution error: {str(e)}")

# Mount static frontend interface files
app.mount("/", StaticFiles(directory="public", html=True), name="static")
