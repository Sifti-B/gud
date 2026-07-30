const express = require('express');
const cors = require('cors');
const YTDlpWrap = require('yt-dlp-wrap').default;
const path = require('path');
const fs = require('fs');

const app = express();
app.use(cors());
app.use(express.json());

// Look for yt-dlp binary in the project folder
const ytDlpPath = path.join(__dirname, 'yt-dlp');
let ytDlpWrap;

// Initialize yt-dlp binary
async function initYtdlp() {
    if (!fs.existsSync(ytDlpPath)) {
        console.log('Downloading latest yt-dlp binary...');
        await YTDlpWrap.downloadFromGithub(ytDlpPath);
        console.log('yt-dlp downloaded successfully!');
    }
    ytDlpWrap = new YTDlpWrap(ytDlpPath);
}
initYtdlp();

// Endpoint 1: Get available qualities and info
app.post('/api/info', async (req, res) => {
    const { url } = req.body;
    if (!url) return res.status(400).json({ error: 'URL is required' });

    try {
        let metadata = await ytDlpWrap.getVideoInfo(url);
        
        // Filter out useful formats (MP4/WebM with distinct resolutions)
        let formats = metadata.formats
            .filter(f => f.vcodec !== 'none' || f.acodec !== 'none')
            .map(f => ({
                formatId: f.format_id,
                resolution: f.resolution || `${f.width}x${f.height}` || 'Audio Only',
                ext: f.ext,
                note: f.format_note || ''
            }));

        res.json({
            title: metadata.title,
            thumbnail: metadata.thumbnail,
            duration: metadata.duration_string,
            formats: formats
        });
    } catch (err) {
        res.status(500).json({ error: 'Failed to fetch video metadata', details: err.message });
    }
});

// Endpoint 2: Stream the file download
app.get('/api/download', (req, res) => {
    const { url, formatId, title } = req.query;
    if (!url || !formatId) return res.status(400).send('Missing parameters');

    const safeTitle = (title || 'video').replace(/[^a-zA-Z0-9]/g, '_');
    
    res.header('Content-Disposition', `attachment; filename="${safeTitle}.mp4"`);

    // Stream the data directly from yt-dlp directly to the browser response
    let ytDlpStream = ytDlpWrap.execStream([
        url,
        '-f', formatId
    ]);

    ytDlpStream.pipe(res);

    ytDlpStream.on('error', (err) => {
        console.error('Download stream error:', err);
    });
});

// Serve frontend interface
app.use(express.static('public'));

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
