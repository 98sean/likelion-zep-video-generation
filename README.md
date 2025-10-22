# Likelion & Zep - Video Generation

## Setup Guide & how to run the code

1. **Clone the repository**
    ```bash
    git clone https://github.com/<your-org>/<your-repo>.git
    cd <your-repo>

2. **Create and activate a virtual environment**
     ```bash
    python -m venv .venv
    source .venv/bin/activate        # Windows: .venv\Scripts\activate
   
3. **Install dependencies**
    ```bash
    pip install -r requirements.txt
   
4. **Verify installation**
    ```bash
    python -c "import moviepy, numpy, PIL, imageio; print('OK')"

5. **Run auto_generation.py**
   ```bash
   python auto_generation.py
