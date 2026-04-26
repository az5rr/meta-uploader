from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path


API_BASE = "http://127.0.0.1:8000"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
PYTHON_BIN = str(DEFAULT_PYTHON if DEFAULT_PYTHON.exists() else Path(os.environ.get("META_UPLOADER_PYTHON", "python3")))
PREPARE_SCRIPT = str(PROJECT_ROOT / "bin" / "prepare_and_schedule.py")
REEL_SOURCE = f"file://{PROJECT_ROOT / 'inbox' / 'example.mp4'}"
POST1_SOURCE = f"file://{PROJECT_ROOT / 'runtime' / 'generated_posts' / 'post1_fadhkuruni.png'}"
POST2_SOURCE = f"file://{PROJECT_ROOT / 'runtime' / 'generated_posts' / 'post2_rabbana.png'}"
POST3_SOURCE = f"file://{PROJECT_ROOT / 'runtime' / 'generated_posts' / 'post3_yusra.png'}"

CANCEL_JOB_IDS = [28, 32, 30, 31, 35, 33, 34, 38]

SCHEDULE = [
    {
        "source": REEL_SOURCE,
        "caption": "أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ\n\nSurely, in the remembrance of Allah do hearts find rest.\n\nذِكْرُ اللَّهِ سَكِينَةٌ لِلْقَلْبِ.\n\n#quran #islam #dhikr #قرآن #ذكر #طمأنينة #islamicreminder",
        "publish_at": "2026-04-19T02:00:00+00:00",
        "media_type": "REEL",
    },
    {
        "source": POST1_SOURCE,
        "caption": "فَاذْكُرُونِي أَذْكُرْكُمْ\n\nSo remember Me; I will remember you.\n\nمِنْ أَلْطَفِ الْآيَاتِ فِي الْقُرْبِ وَالذِّكْرِ.\n\n#quran #islam #ذكر #قرآن #طمأنينة #islamicreminder",
        "publish_at": "2026-04-19T05:00:00+00:00",
        "media_type": "POST",
    },
    {
        "source": REEL_SOURCE,
        "caption": "وَهُوَ مَعَكُمْ أَيْنَ مَا كُنْتُمْ\n\nHe is with you wherever you are.\n\nمَعِيَّةُ اللَّهِ تُورِثُ الطُّمَأْنِينَةَ.\n\n#quran #islam #tawakkul #قرآن #سكينة #توكل",
        "publish_at": "2026-04-19T16:00:00+00:00",
        "media_type": "REEL",
    },
    {
        "source": POST2_SOURCE,
        "caption": "رَبَّنَا لَا تُزِغْ قُلُوبَنَا بَعْدَ إِذْ هَدَيْتَنَا وَهَبْ لَنَا مِنْ لَدُنْكَ رَحْمَةً ۚ إِنَّكَ أَنْتَ الْوَهَّابُ\n\nOur Lord, do not let our hearts deviate after You have guided us.\n\nنَسْأَلُ اللَّهَ الثَّبَاتَ وَالرَّحْمَةَ.\n\n#dua #quran #islam #دعاء #قرآن #رحمة #ثبات",
        "publish_at": "2026-04-20T05:00:00+00:00",
        "media_type": "POST",
    },
    {
        "source": REEL_SOURCE,
        "caption": "رَبِّ اشْرَحْ لِي صَدْرِي ۝ وَيَسِّرْ لِي أَمْرِي\n\nMy Lord, expand my chest and ease my task for me.\n\nدُعَاءٌ يُقَالُ فِي لَحَظَاتِ الثِّقَلِ وَالْبِدَايَاتِ.\n\n#dua #islam #quran #دعاء #يسر #طمأنينة",
        "publish_at": "2026-04-20T16:00:00+00:00",
        "media_type": "REEL",
    },
    {
        "source": POST3_SOURCE,
        "caption": "فَإِنَّ مَعَ الْعُسْرِ يُسْرًا\n\nIndeed, with hardship comes ease.\n\nوَعْدٌ يُعِيدُ لِلرُّوحِ هُدُوءَهَا.\n\n#quran #islam #sabr #قرآن #فرج #صبر",
        "publish_at": "2026-04-21T05:00:00+00:00",
        "media_type": "POST",
    },
]


def patch_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="PATCH",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def cancel_conflicts() -> None:
    for job_id in CANCEL_JOB_IDS:
        result = patch_json(f"{API_BASE}/jobs/{job_id}", {"status": "cancelled"})
        print(f"cancelled job {result['id']} at {result['publish_at']}")


def create_jobs() -> None:
    for item in SCHEDULE:
        result = subprocess.run(
            [
                PYTHON_BIN,
                PREPARE_SCRIPT,
                item["source"],
                item["caption"],
                item["publish_at"],
                item["media_type"],
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        print(result.stdout.strip())


def main() -> None:
    cancel_conflicts()
    create_jobs()


if __name__ == "__main__":
    main()
