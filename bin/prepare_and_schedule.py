#!/usr/bin/env python3
from __future__ import annotations

import json
import mimetypes
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
PYTHON_BIN = Path(os.environ.get("META_UPLOADER_PYTHON", str(DEFAULT_PYTHON if DEFAULT_PYTHON.exists() else Path(sys.executable))))
RUNTIME_DIR = PROJECT_ROOT / "runtime" / "media"
API_URL = 'http://127.0.0.1:8000/jobs'
CATBOX_API = 'https://catbox.moe/user/api.php'
DIRECT_EXTENSIONS = {'.mp4', '.mov', '.m4v', '.jpg', '.jpeg', '.png', '.webp'}


def infer_extension(url: str, media_type: str) -> str:
    path = urllib.parse.urlparse(url).path
    ext = Path(path).suffix.lower()
    if ext in DIRECT_EXTENSIONS:
        return ext
    return '.mp4' if media_type == 'REEL' else '.png'


def download_direct(url: str, dest: Path) -> None:
    subprocess.run(
        ['curl', '-fsSL', url, '-o', str(dest)],
        check=True,
        capture_output=True,
        text=True,
        timeout=300,
    )


def download_via_ytdlp(url: str, dest: Path) -> None:
    subprocess.run(
        [
            str(PYTHON_BIN),
            '-m',
            'yt_dlp',
            '--no-playlist',
            '--no-progress',
            '--no-warnings',
            '-f',
            'best',
            '-S',
            'res,br,fps,size',
            '-o',
            str(dest),
            url,
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def stage_to_catbox(path: Path) -> str:
    result = subprocess.run(
        [
            'curl',
            '-fsS',
            '-F',
            'reqtype=fileupload',
            '-F',
            f'fileToUpload=@{path}',
            CATBOX_API,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=300,
    )
    url = result.stdout.strip()
    if not url.startswith('https://files.catbox.moe/'):
        raise RuntimeError(f'Unexpected Catbox response: {url}')
    return url


def create_job(staged_url: str, caption: str, publish_at: str, media_type: str) -> dict:
    payload = {
        'video_url': staged_url,
        'caption': caption,
        'publish_at': publish_at,
        'media_type': media_type,
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode())


def main() -> int:
    if len(sys.argv) != 5:
        print('usage: prepare_and_schedule.py <source_url> <caption> <publish_at> <REEL|POST>', file=sys.stderr)
        return 1

    source_url, caption, publish_at, media_type = sys.argv[1:5]
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    if media_type not in {'REEL', 'POST'}:
        raise RuntimeError('media_type must be REEL or POST')

    ext = infer_extension(source_url, media_type)
    temp_path = RUNTIME_DIR / f'{uuid4().hex}{ext}'
    parsed = urllib.parse.urlparse(source_url)

    try:
        if parsed.netloc.endswith('instagram.com') or parsed.netloc.endswith('www.instagram.com'):
            download_via_ytdlp(source_url, temp_path)
        else:
            download_direct(source_url, temp_path)

        if temp_path.suffix.lower() not in DIRECT_EXTENSIONS:
            guessed, _ = mimetypes.guess_type(temp_path.name)
            if guessed == 'video/mp4' and temp_path.suffix.lower() != '.mp4':
                new_path = temp_path.with_suffix('.mp4')
                temp_path.rename(new_path)
                temp_path = new_path

        staged_url = stage_to_catbox(temp_path)
        job = create_job(staged_url, caption, publish_at, media_type)
        print(json.dumps({'source_url': source_url, 'staged_url': staged_url, 'job': job}, ensure_ascii=False))
        return 0
    finally:
        try:
            if temp_path.exists():
                temp_path.unlink()
        except OSError:
            pass


if __name__ == '__main__':
    raise SystemExit(main())
