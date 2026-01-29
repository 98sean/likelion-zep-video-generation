# Likelion & Zep - Video Generation

A FastAPI-based system for automatically generating quiz videos from trending topics. This project fetches trending data, generates quizzes using OpenAI, and creates video content with MoviePy.

## Features

- **Quiz Generation**: Automatically create quizzes from trending topics using Google Trends or SerpAPI
- **Video Creation**: Generate MP4 videos from quiz data using MoviePy
- **FastAPI Server**: RESTful API for managing batch operations
- **Batch Processing**: Process multiple quizzes and videos in a single workflow

## Install

### Prerequisites

- Python 3.8 or higher
- FFmpeg (required by MoviePy)

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/likelion-zep-video-generation.git
cd likelion-zep-video-generation
```

### 2. Create and Activate Virtual Environment

```bash
# On Linux/macOS
python -m venv .venv
source .venv/bin/activate

# On Windows
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables

Run the setup script to configure API keys:

```bash
python setup_env.py
```

This will prompt you to enter:
- **OpenAI API Key** (required)
- **SerpAPI API Key** (optional, for enhanced trending data)

The script creates a `.env` file with your credentials. **Important**: `.env` is already in `.gitignore` to prevent accidental credential exposure.

### 5. Verify Installation

```bash
python -c "import moviepy, numpy, PIL, imageio, fastapi; print('✓ All dependencies installed')"
```

## Usage

### Running the FastAPI Server

Start the development server:

```bash
uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
```

The server will be available at `http://localhost:8000`

Check API documentation:
- Interactive docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### API Endpoints

#### Health Check
```bash
GET /health
```

#### Generate Quizzes from Trending Topics
```bash
POST /quiz-batch
```
Fetches trending topics and generates quizzes, saving results to `data/` directory.

#### Generate Videos from Quiz File
```bash
POST /video-batch
Content-Type: application/json

{
  "quiz_file_name": "quiz_2024-12-04_batch1.json"
}
```
Generates MP4 videos from quiz JSON file, saves to `videos/` directory.

#### List Quiz Files
```bash
GET /quizzes
```
Returns list of all quiz JSON files in `data/` directory.

#### Download Quiz File
```bash
GET /quizzes/{filename}/download
```

#### List Video Files
```bash
GET /videos
```
Returns list of all generated MP4 videos in `videos/` directory.

#### Download Video File
```bash
GET /videos/{filename}/download
```

### Running Batch Jobs Directly

#### Generate Quizzes
```bash
python -m src.quiz_batch
```

#### Generate Videos
```bash
python -m src.generate_quiz_video
```

#### Auto-Schedule Quiz Generation
```bash
python -m src.auto_quiz_scheduler
```

## Project Structure

```
.
├── src/
│   ├── app.py                      # FastAPI application
│   ├── config.py                   # Configuration and environment variables
│   ├── quiz_batch.py               # Batch quiz generation
│   ├── generate_quiz.py            # Quiz generation logic
│   ├── generate_quiz_video.py      # Video generation from quizzes
│   ├── auto_quiz_scheduler.py      # Scheduled quiz generation
│   ├── fetch_trends_serpapi.py     # Fetch trending topics
│   └── auto_upload_shorts.py       # YouTube Shorts upload automation
├── data/                           # Generated quiz JSON files (created at runtime)
├── videos/                         # Generated MP4 videos (created at runtime)
├── assets/                         # Design assets and fonts
│   ├── fonts/                      # Custom fonts for videos
│   ├── sports_balls/               # Design elements
│   ├── v1_design/                  # Design v1 assets
│   └── v2_design/                  # Design v2 assets
├── requirements.txt                # Python dependencies
├── setup_env.py                    # Environment setup script
├── .env                            # Environment variables (git-ignored)
├── .gitignore                      # Git ignore rules
├── Dockerfile                      # Docker configuration
└── docker-compose.yml              # Docker Compose configuration

```

## Dependencies

Key dependencies:
- **FastAPI**: Web framework for the API
- **MoviePy**: Video generation and editing
- **OpenAI**: AI-powered quiz generation
- **PyTrends**: Google Trends data fetching
- **Google API Client**: YouTube integration
- **imageio-ffmpeg**: Video codec support
- **Pillow**: Image processing

See `requirements.txt` for the complete list.

## Docker Support

Build and run with Docker:

```bash
# Build image
docker build -t zep-video-gen .

# Run with Docker Compose
docker-compose up
```

## Troubleshooting

### ModuleNotFoundError
Ensure virtual environment is activated and dependencies are installed:
```bash
source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

### FFmpeg Not Found
Install FFmpeg:
- **Ubuntu/Debian**: `sudo apt-get install ffmpeg`
- **macOS**: `brew install ffmpeg`
- **Windows**: Download from https://ffmpeg.org/download.html

### API Key Issues
Re-run setup to update credentials:
```bash
python setup_env.py
```

## License

[Add your license here]

## Contributors

- Likelion & Zep Team
