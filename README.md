# Likelion & Zep - Video Generation

A FastAPI-based system for automatically generating quiz videos from trending topics. This project fetches trending data, generates quizzes using OpenAI, and creates video content with MoviePy.

## Features

- **Quiz Generation**: Automatically create quizzes from trending topics using Google Trends or SerpAPI
- **Video Creation**: Generate MP4 videos from quiz data using MoviePy
- **FastAPI Server**: RESTful API for managing batch operations
- **Batch Processing**: Process multiple quizzes and videos in a single workflow

## Data Flow

The system follows a multi-stage pipeline from trend fetching to video publishing:

```mermaid
graph LR
    A[Google Trends/<br/>SerpAPI] -->|Fetch trending<br/>topics| B[fetch_trends_serpapi.py]
    B -->|Topic keywords| C[OpenAI API<br/>GPT-4]
    C -->|Generate quiz<br/>questions| D[generate_quiz.py]
    D -->|Validate &<br/>structure| E[Quiz JSON<br/>data/]
    E -->|Load quiz data| F[MoviePy +<br/>Pillow]
    F -->|Render frames<br/>& audio| G[MP4 Video<br/>videos/]
    G -->|Upload| H[YouTube<br/>Shorts]

    style A fill:#e1f5ff
    style C fill:#fff4e1
    style E fill:#e8f5e9
    style G fill:#fce4ec
    style H fill:#f3e5f5
```

**Pipeline Stages:**

1. **Trend Fetching**: SerpAPI queries Google Trends for trending sports topics (configurable by region/category)
2. **Quiz Generation**: OpenAI GPT models create multiple-choice questions with validation
   - Primary generation: GPT-5-mini creates quiz questions
   - Validation: GPT-5.1 fact-checks answers and validates question quality
   - Retries up to 3 times to reach target of 10 valid questions per topic
3. **JSON Storage**: Validated quizzes saved to `data/quizzes_output_N.json` with structured schema
4. **Video Rendering**: MoviePy generates 9:16 vertical videos (60 seconds)
   - Dynamic text rendering with custom fonts
   - Theme-based design (purple/green/blue)
   - Countdown animation + answer reveal
   - Background music + sound effects
5. **YouTube Upload**: Automated upload to YouTube Shorts with optimized metadata

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

## Configuration Reference

All configuration is managed through environment variables loaded from the `.env` file. Use `python setup_env.py` to create and configure this file interactively.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | **Yes** | None | OpenAI API key for quiz generation. Used by GPT-5-mini (quiz creation) and GPT-5.1 (validation). Get your key at https://platform.openai.com/api-keys |
| `SERPAPI_API_KEY` | No | None | SerpAPI key for fetching Google Trends data. If not provided, you'll need to use alternative trend sources or manually provide topics. Get your key at https://serpapi.com/manage-api-key |
| `DATA_DIR` | No | `"data"` | Directory path for storing generated quiz JSON files. Created automatically if it doesn't exist. Configured in `src/config.py` |
| `VIDEOS_DIR` | No | `"videos"` | Directory path for storing generated MP4 video files. Created automatically if it doesn't exist. Configured in `src/config.py` |

**Note**: The `.env` file is git-ignored by default to protect your API credentials. Never commit this file to version control.

### Advanced Configuration

You can modify additional settings directly in the source files:

- **Quiz Parameters** (`src/generate_quiz.py`):
  - `TARGET_COUNT = 10`: Number of quiz questions to generate per topic
  - `KNOWLEDGE_CUTOFF = "May 2024"`: AI knowledge cutoff date for fact validation
  - `max_trial = 3`: Maximum retry attempts for quiz generation

- **Video Settings** (`src/generate_quiz_video.py`):
  - `W, H = 1080, 1920`: Video dimensions (9:16 vertical format)
  - `FPS = 30`: Frames per second
  - `COUNTDOWN_SECONDS = 5`: Question display duration
  - `ANSWER_HOLD = 2`: Answer reveal display duration
  - `AVAILABLE_THEMES = ["purple", "green", "blue"]`: Color themes for videos

- **Trend Fetching** (`src/fetch_trends_serpapi.py`):
  - `geo = "US"`: Region code for trends (e.g., "US", "KR", "GB")
  - `category_id = 17`: Google Trends category (17 = Sports, 16 = Entertainment)
  - `hours = 4`: Time window for trends (4, 24, 48, or 168 hours)

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
