import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

CURRENT_DIR = Path(__file__).resolve().parent
PREDICT_SCRIPT: Optional[Path] = None
for candidate in [
	CURRENT_DIR / "Model_ML" / "predict.py",
	CURRENT_DIR.parent / "Model_ML" / "predict.py",
	CURRENT_DIR.parent / "py_api" / "Model_ML" / "predict.py",
	CURRENT_DIR.parent.parent / "Model_ML" / "predict.py",
]:
	if candidate.is_file():
		PREDICT_SCRIPT = candidate
		break

if PREDICT_SCRIPT:
	print(f"[sentiment] Using predict script at {PREDICT_SCRIPT}", file=sys.stderr)

def predict_sentiment(text: str) -> int:
	if not text or not text.strip():
		print("[sentiment] Empty text, defaulting to positive", file=sys.stderr)
		return 1
	if PREDICT_SCRIPT is None:
		print("[sentiment] Predict script not found in candidate paths", file=sys.stderr)
		return 1

	# Try common python executables
	candidates = ["python3", "python"]
	for exe in candidates:
		try:
			out = subprocess.check_output(
				[exe, str(PREDICT_SCRIPT), text],
				env={**os.environ, "PYTHONIOENCODING": "utf-8"},
				stderr=subprocess.STDOUT,
				timeout=30,
			).decode("utf-8", errors="ignore").strip()
			if out:
				if out.isdigit():
					return 1 if int(out) != 0 else 0
				low = out.lower()
				if "neg" in low:
					return 0
				return 1
		except Exception as exc:
			print(f"[sentiment] {exe} failed: {exc}", file=sys.stderr)
			continue
	print("[sentiment] All python candidates failed, defaulting to positive", file=sys.stderr)
	return 1


