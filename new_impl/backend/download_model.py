#!/usr/bin/env python3
"""
Download Vosk Portuguese model for teleprompter.
Run this script before building the Docker image.
"""

import os
import sys
import urllib.request
import zipfile
import shutil
from pathlib import Path

MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-pt-fb-v0.1.1-20220516_2113.zip"
MODEL_NAME = "vosk-model-pt-fb-v0.1.1-20220516_2113"
TARGET_DIR = "models"
TARGET_NAME = "vosk-model-pt"


def download_model():
    models_dir = Path(TARGET_DIR)
    models_dir.mkdir(exist_ok=True)

    zip_path = models_dir / f"{MODEL_NAME}.zip"
    extract_dir = models_dir / MODEL_NAME
    target_path = models_dir / TARGET_NAME

    if target_path.exists():
        print(f"Model already exists at {target_path}")
        return

    print(f"Downloading Vosk model from {MODEL_URL}...")
    try:
        urllib.request.urlretrieve(MODEL_URL, zip_path)
        print("Download complete.")
    except Exception as e:
        print(f"Failed to download model: {e}")
        sys.exit(1)

    print(f"Extracting to {extract_dir}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(models_dir)
    except Exception as e:
        print(f"Failed to extract model: {e}")
        sys.exit(1)

    print(f"Renaming {extract_dir} to {target_path}...")
    if target_path.exists():
        shutil.rmtree(target_path)
    shutil.move(str(extract_dir), str(target_path))

    # Disable rescore as per original setup
    rescore_dir = target_path / "rescore"
    if rescore_dir.exists():
        rescore_disable = target_path / "rescore_disable"
        shutil.move(str(rescore_dir), str(rescore_disable))
        print("Renamed rescore to rescore_disable")

    # Clean up zip
    zip_path.unlink()
    print(f"Model ready at {target_path}")


if __name__ == "__main__":
    download_model()