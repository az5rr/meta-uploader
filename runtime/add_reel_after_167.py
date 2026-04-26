from __future__ import annotations

import os
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
PYTHON_BIN = str(DEFAULT_PYTHON if DEFAULT_PYTHON.exists() else Path(os.environ.get("META_UPLOADER_PYTHON", "python3")))
PREPARE_SCRIPT = str(PROJECT_ROOT / "bin" / "prepare_and_schedule.py")
REEL_SOURCE = f"file://{PROJECT_ROOT / 'inbox' / 'example.mp4'}"


def main() -> None:
    result = subprocess.run(
        [
            PYTHON_BIN,
            PREPARE_SCRIPT,
            REEL_SOURCE,
            "اللَّهُمَّ اجْعَلِ الْقُرْآنَ رَبِيعَ قُلُوبِنَا وَنُورَ صُدُورِنَا\n\n"
            "O Allah, make the Qur'an the spring of our hearts and the light of our chests.\n\n"
            "اللَّهُمَّ ارْزُقْنَا أُنْسَ الْقُرْآنِ.\n\n"
            "#quran #dua #islam #قرآن #دعاء #نور #ذكر",
            "2026-04-20T02:00:00+00:00",
            "REEL",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    print(result.stdout.strip())


if __name__ == "__main__":
    main()
