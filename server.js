const express = require('express');
const cors = require('cors');
const YTDlpWrap = require('yt-dlp-wrap').default;

const app = express();
app.use(cors());
app.use(express.json());

const ytDlpWrap = new YTDlpWrap('/usr/local/bin/yt-dlp');

const USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

// Endpoint 1: Fetch metadata qualities
app.post('/api/info', async (req, res) => {
    const { url } = req.body;
    if (!url) return res.status(400).json({ error: 'URL is required' });

    try {
        // Base browser spoofing arguments
        let args = [
            url,
            '--user-agent', USER_AGENT,
            '--no-check-certificates'
        ];

        // PROXY IMPLEMENTATION: Check if a proxy is configured on Render
        if (process.env.PROXY_URL) {
            console.log(`Routing metadata lookup through proxy: ${process.env.PROXY_URL}`);
            args.push('--proxy', process.env.PROXY_URL);
        } else {
            console.log('Running lookup without proxy (using standard datacenter IP)');
        }

        let metadata = await ytDlpWrap.getVideoInfo(args);
        
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

// Endpoint 2: Direct Stream Download
app.get('/api/download', (req, res) => {
    const { url, formatId, title } = req.query;
    if (!url || !formatId) return res.status(400).send('Missing parameters');

    const safeTitle = (title || 'video').replace(/[^a-zA-Z0-9]/g, '_');
    res.header('Content-Disposition', `attachment; filename="${safeTitle}.mp4"`);

    let args = [
        url,
        '-f', formatId,
        '--user-agent', USER_AGENT,
        '--no-check-certificates'
    ];

    // Route download data stream through the proxy if configured
    if (process.env.PROXY_URL) {
        args.push('--proxy', process.env.PROXY_URL);
    }

    let ytDlpStream = ytDlpWrap.execStream(args);
    ytDlpStream.pipe(res);

    ytDlpStream.on('error', (err) => {
        console.error('Download stream error:', err);
    });
});

app.use(express.static('public'));

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running smoothly on port ${PORT}`));
