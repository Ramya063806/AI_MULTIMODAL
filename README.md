# Multimodal Document Analyzer

A beginner-friendly Streamlit app for analyzing PDFs, scanned documents, and images.

## What it does

- Extracts text from PDFs and images
- Preserves reading order as much as possible with document parsing tools
- Detects tables in PDFs
- Extracts simple form-like label/value pairs
- Describes embedded visual elements using OCR and image metadata
- Groups content into logical sections with a Smart Section Navigator

## Local setup

1. Install Python 3.10 or newer.
2. Install Tesseract OCR on your machine.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the app:

```bash
streamlit run app.py
```

5. Add your Groq API key in a `.env` file if you want multimodal AI summaries:

```bash
GROQ_API_KEY=your_key_here
GROQ_VISION_MODEL=llama-3.2-90b-vision-preview
```

## Notes

- The app only analyzes actual uploaded content.
- Table extraction works best on text-based PDFs.
- OCR quality depends on image clarity and the local Tesseract installation.

## Deploy to Streamlit Community Cloud

1. Push this project to a GitHub repository.
2. Make sure these files are committed:
   - `app.py`
   - `requirements.txt`
   - `packages.txt`
   - `.streamlit/config.toml`
   - `src/`
3. Go to `https://share.streamlit.io/` and choose **New app**.
4. Select your repository, branch, and set the main file path to:

```text
app.py
```

5. Add secrets in **Advanced settings** if you use Groq:

```toml
GROQ_API_KEY = "your_key_here"
GROQ_VISION_MODEL = "llama-3.2-90b-vision-preview"
```

6. Click **Deploy**.

`packages.txt` installs Tesseract OCR and Poppler on Streamlit Cloud so scanned PDFs and images can be processed.

## Deploy on Render

1. Push this project to GitHub.
2. Create a new **Web Service** on Render and connect the repository.
3. Use the included `Dockerfile` so Render installs system dependencies like Tesseract OCR and Poppler.
4. If you choose a Docker service, Render will build the image automatically from `Dockerfile`.
5. Add environment variables if needed:

```text
GROQ_API_KEY=your_key_here
GROQ_VISION_MODEL=llama-3.2-90b-vision-preview
```

6. If you prefer Render's standard Python service instead of Docker, set these commands:

```bash
pip install -r requirements.txt
```

```bash
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

7. For OCR and scanned PDF support on Render, the Docker-based deployment is recommended because it installs Tesseract and Poppler automatically.
