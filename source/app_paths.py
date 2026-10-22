"""Separate packaged, read-only resources from portable, local game data."""
from pathlib import Path
import sys

SOURCE_DIR=Path(__file__).resolve().parent
APP_DIR=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else SOURCE_DIR
RESOURCE_DIR=Path(getattr(sys,'_MEIPASS',SOURCE_DIR))
DATA_DIR=APP_DIR/'data'
ASSET_DIR=RESOURCE_DIR/'assets'
