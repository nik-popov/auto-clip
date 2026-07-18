# auto-clip

Low-cost pipeline to detect likely drops in long DJ sets and render short clips for social distribution.

## What This MVP Does

- Accepts a YouTube URL or local media file as input.
- Extracts mono WAV audio with ffmpeg for analysis.
- Detects high-energy moments using onset, RMS, and spectral-change features.
- Selects spaced drop candidates with score-based ranking.
- Renders short clips with ffmpeg.
- Supports both fast copy cuts and optional 9:16 formatted exports.
- Writes a machine-readable run report.

## Stack

- Python 3.11+
- ffmpeg
- yt-dlp (required for URL input)
- librosa + numpy

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies.
3. Run the pipeline.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

# Local file input
auto-clip /path/to/your_set.mp4

# YouTube input
auto-clip "https://www.youtube.com/watch?v=..."
```

Use a custom config:

```bash
cp config.example.json config.local.json
auto-clip "https://www.youtube.com/watch?v=..." --config config.local.json
```

## Config Fields

- `clip_duration_seconds`: Output clip length.
- `pre_drop_seconds`: How many seconds before the detected drop to start each clip.
- `max_clips`: Maximum clips to export per source.
- `min_spacing_seconds`: Minimum distance between selected drop points.
- `sample_rate`: Audio analysis sample rate.
- `render_vertical_9x16`: If true, re-encodes output to 1080x1920 style layout with blurred background.
- `use_youtube_heatmap`: If true (default), blends YouTube "Most Replayed" audience data into drop scoring for YouTube sources.
- `heatmap_weight`: 0-1 blend weight of audience replay data vs pure audio analysis (default 0.5).
- `dry_run`: If true, prints ffmpeg/yt-dlp commands without running them.
- `output_dir`: Clip output root directory.

## Output Layout

```text
artifacts/
	<source_id>/
		source.mp4
		source.wav
		run_summary.json

outputs/
	<source_id>/
		clip_01_<timestamp>.mp4
		clip_02_<timestamp>.mp4
```

## Development

Run tests:

```bash
pytest
```

## Cloudflare Worker Gateway

The main clip engine requires Python and ffmpeg, which are not executable inside Cloudflare Workers runtime.
This repository includes a Worker gateway for request intake and queueing under [worker/src/index.js](worker/src/index.js).

### Worker Endpoints

- `GET /`: browser UI for submitting jobs.
- `GET /health`: readiness check.
- `POST /jobs`: accepts JSON payload with `source` and optional `config`.

### Queue Consumer Behavior

The Worker now has a queue consumer for `auto-clip-jobs`.

- If `PROCESSOR_WEBHOOK` is configured, each queued job is forwarded to that HTTP endpoint.
- If `PROCESSOR_WEBHOOK` is not configured, jobs are still accepted and queued, and consumer logs each payload.

Set webhook URL:

```bash
cd worker
npx wrangler secret put PROCESSOR_WEBHOOK
```

If the UI shows `"mode": "queued"`, that means intake is working and the job was accepted.
Actual clip creation happens in the processor service.

### Run the Processor Service

Start the Python processor webhook locally:

```bash
source .venv/bin/activate
auto-clip-processor --host 0.0.0.0 --port 8080 --work-dir artifacts
```

Health check:

```bash
curl http://127.0.0.1:8080/health
```

Manual processing test:

```bash
curl -X POST http://127.0.0.1:8080/process \
	-H "content-type: application/json" \
	-d '{"source":"https://www.youtube.com/watch?v=example"}'
```

To connect Worker queue to processor:

1. Host the processor on a publicly reachable URL (for example VPS, Fly.io, Railway, Render).
2. Set Worker secret `PROCESSOR_WEBHOOK` to `https://your-host/process`.
3. Re-deploy Worker:

```bash
cd worker
npx wrangler deploy
```

Example:

```bash
curl -X POST http://127.0.0.1:8787/jobs \
	-H "content-type: application/json" \
	-d '{"source":"https://www.youtube.com/watch?v=example"}'
```

### Local Worker Test

```bash
cd worker
npm install
npm run dev
```

### Deploy Worker

```bash
cd worker
npm run check
npm run deploy
```

If this is your first deploy, authenticate with Wrangler:

```bash
npx wrangler login
```

## Notes

- ffmpeg stream copy mode (`-c copy`) is fast but cuts on keyframe boundaries.
- Vertical mode re-encodes for consistent 9:16 output.
- Current detector is feature-based and unsupervised. Tracklist-assisted logic can be added in the next iteration.