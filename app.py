import os
import time
import json
import whisper
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".m4a"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".flv"}
SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS

DEFAULT_DIRECTORY = Path(__file__).parent

model = whisper.load_model("tiny")

TRACKING_FILE = DEFAULT_DIRECTORY / "processed_files.json"

def load_processed_files():
    if TRACKING_FILE.exists():
        with open(TRACKING_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_processed_files(processed_files):
    with open(TRACKING_FILE, "w", encoding="utf-8") as f:
        json.dump(list(processed_files), f)

def transcribe_audio(file_path):
    file_path = Path(file_path)
    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return
    
    print(f"Transcribing: {file_path.name}...")

    try:
        result = model.transcribe(str(file_path))
        transcript = result["text"]

        txt_filename = file_path.with_suffix(".txt")
        with open(txt_filename, "w", encoding="utf-8") as f:
            f.write(transcript)

        print(f"Saved transcript: {txt_filename}")
        return str(file_path)
    except Exception as e:
        print(f"Error processing {file_path.name}: {e}")
        return None

def scan_existing_files():
    processed_files = load_processed_files()
    media_files = {str(f) for f in DEFAULT_DIRECTORY.rglob("*") if f.suffix.lower() in SUPPORTED_EXTENSIONS}

    new_files = media_files - processed_files
    for file in new_files:
        if transcribe_audio(file):
            processed_files.add(file)

    save_processed_files(processed_files)

class MediaFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            print(f"New file detected: {file_path.name}")
            processed_files = load_processed_files()

            if str(file_path) not in processed_files:
                if transcribe_audio(file_path):
                    processed_files.add(str(file_path))
                    save_processed_files(processed_files)

if __name__ == "__main__":
    print(f"Monitoring directory: {DEFAULT_DIRECTORY}")

    scan_existing_files()

    event_handler = MediaFileHandler()
    observer = Observer()
    observer.schedule(event_handler, path=str(DEFAULT_DIRECTORY), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopped monitoring.")

    observer.join()
