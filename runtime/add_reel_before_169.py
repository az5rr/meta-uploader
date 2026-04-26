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
            "سُبْحَانَ اللَّهِ وَبِحَمْدِهِ، سُبْحَانَ اللَّهِ الْعَظِيمِ\n\n"
            "Glory be to Allah and praise be to Him; glory be to Allah, the Magnificent.\n\n"
            "ذِكْرٌ خَفِيفٌ عَلَى اللِّسَانِ، عَظِيمٌ فِي الْمِيزَانِ.\n\n"
            "#dhikr #islam #quran #ذكر #قرآن #طمأنينة #تسبيح",
            "2026-04-21T02:00:00+00:00",
            "REEL",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    print(result.stdout.strip())


if __name__ == "__main__":
    main()
