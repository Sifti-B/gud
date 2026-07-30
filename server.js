const express = require('express');
const cors = require('cors');
const YTDlpWrap = require('yt-dlp-wrap').default;
const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');

const app = express();
app.use(cors());
app.use(express.json());

const ytDlpPath = path.join(__dirname, 'yt-dlp');
let ytDlpWrap;

// Upgraded Initializer to handle Linux Server permissions
async function initYtdlp() {
    try {
        if (!fs.existsSync(ytDlpPath)) {
            console.log('Downloading latest yt-dlp binary from GitHub...');
            await YTDlpWrap.downloadFromGithub(ytDlpPath);
            console.log('yt-dlp downloaded successfully!');
        }
        
        // CRUCIAL FOR LINUX/RENDER: Give the file execution permissions
        if (process.platform !== 'win32') {
            console.log('Applying Linux execution permissions to yt-dlp...');
            execSync(`chmod +x "${ytDlpPath}"`);
        }

        ytDlpWrap = new YTDlpWrap(ytDlpPath);
        console.log('yt-dlp engine successfully armed and ready.');
    } catch (error) {
        console.error('Initialization error during core setup:', error.message);
    }
}
initYtdlp();

// Endpoint 1: Get available qualities and info
app.post('/api/info', async (req, res) => {
    const { url } = req.body;
    if (!url) return res.status(400).json({ error: 'URL is required' });
    if (!ytDlpWrap) return res.status(503).json({ error: 'Server is still booting up the engine. Please refresh in 10 seconds.' });

    try {
        let metadata = await ytDlpWrap.getVideoInfo(url);
        
        if (!metadata || !metadata.formats) {
            throw new Error("No format data found for this link.");
        }

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
        console.error('Metadata Fetch Error:', err.message);
        res.status(500).json({ error: 'Failed to fetch video metadata', details: err.message });
    }
});

// Endpoint 2: Stream the file download
app.get('/api/download', (req, res) => {
    const { url, formatId, title } = req.query;
    if (!url || !formatId) return res.status(400).send('Missing parameters');

    const safeTitle = (title || 'video').replace(/[^a-zA-Z0-9]/g, '_');
    res.header('Content-Disposition', `attachment; filename="${safeTitle}.mp4"`);

    let ytDlpStream = ytDlpWrap.execStream([
        url,
        '-f', formatId
    ]);

    ytDlpStream.pipe(res);

    ytDlpStream.on('error', (err) => {
        console.error('Download stream error:', err);
    });
});

app.use(express.static('public'));

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
