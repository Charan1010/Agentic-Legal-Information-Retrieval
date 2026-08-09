"""
Sync Kaggle cache bundle to local data/processed/ directory.

Usage:
    1. Download cache_bundle.zip from Kaggle notebook Output tab
    2. Place it in the repo root (next to this scripts/ folder)
    3. Run: python scripts/sync_kaggle_caches.py

Or specify a path:
    python scripts/sync_kaggle_caches.py /path/to/cache_bundle.zip
"""

import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCAL_CACHE_DIR = REPO_ROOT / "data" / "processed"
DEFAULT_BUNDLE = REPO_ROOT / "cache_bundle.zip"


def sync(bundle_path: Path):
    if not bundle_path.exists():
        print(f"❌ Bundle not found: {bundle_path}")
        print(f"   Download cache_bundle.zip from Kaggle Output tab")
        print(f"   and place it at: {DEFAULT_BUNDLE}")
        sys.exit(1)

    LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Extracting {bundle_path.name} → {LOCAL_CACHE_DIR}/")
    with zipfile.ZipFile(bundle_path, 'r') as zf:
        for info in zf.infolist():
            size_mb = info.file_size / 1e6
            target = LOCAL_CACHE_DIR / info.filename
            if target.exists():
                existing_size = target.stat().st_size
                if existing_size == info.file_size:
                    print(f"  ⏭️  {info.filename} ({size_mb:.1f} MB) — already up to date")
                    continue
                else:
                    print(f"  🔄 {info.filename} ({size_mb:.1f} MB) — updating (was {existing_size/1e6:.1f} MB)")
            else:
                print(f"  📥 {info.filename} ({size_mb:.1f} MB) — new")
            zf.extract(info, LOCAL_CACHE_DIR)

    print(f"\n✅ Local caches synced to: {LOCAL_CACHE_DIR}")
    print(f"   Files:")
    for f in sorted(LOCAL_CACHE_DIR.iterdir()):
        if f.is_file():
            print(f"     {f.name} — {f.stat().st_size/1e6:.1f} MB")


if __name__ == "__main__":
    bundle = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_BUNDLE
    sync(bundle)
