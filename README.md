# Receipt/Invoice Converter

Gradio app that converts receipt/invoice PNGs inside an uploaded ZIP into structured Markdown or JSON using a local llama.cpp server running the Qwen3-VL-30B-A3B-Instruct vision model.

## Features
- Upload a ZIP of receipts (top-level folders, PNG pages inside).
- Preview receipt pages, select specific receipts or convert all.
- Choose Markdown or JSON output (per receipt file + downloadable ZIP).
- Uses llama.cpp (OpenAI-compatible endpoint) with multimodal prompts.

## Requirements
- Python 3.11+
- llama.cpp server (`llama-server`) running with a vision-capable model.
- Dependencies in `requirements.txt`.

## Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running llama.cpp server
Start `llama-server` with the Qwen3-VL-30B-A3B-Instruct model (update paths as needed):
```bash
./llama-server \
  -m /path/to/Qwen3-VL-30B-A3B-Instruct-Q4_K_M.gguf \
  --mmproj /path/to/mmproj-model.gguf \
  --host 0.0.0.0 --port 8080 \
  --chat-template chatml
```
The app defaults to `LLAMA_BASE_URL=http://localhost:8080/v1`. You can override with env vars:
- `LLAMA_BASE_URL` (default `http://localhost:8080/v1`)
- `LLAMA_MODEL` (default: first model from `/v1/models`)
- `LLAMA_TEMPERATURE` (default `0`)
- `LLAMA_MAX_TOKENS` (default `2048`)

## Running the Gradio app
```bash
source .venv/bin/activate
python app.py
```
Then open the printed Gradio URL.

## ZIP structure
Top-level directories represent receipts. Each folder contains one or more PNG pages. Non-PNG files at the root (e.g., `manifest.json`, `processing_log.txt`) are ignored.

## Output
- Files named `<receipt_name>.md` or `<receipt_name>.json` (sanitized for safety).
- Downloadable ZIP of all generated outputs.

## Error handling
- Safe ZIP extraction (prevents Zip Slip).
- JSON mode retries once with a repair prompt if the response is invalid JSON.

