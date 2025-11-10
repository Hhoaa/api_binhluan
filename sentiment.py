import os
import subprocess
import sys
from typing import Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREDICT_SCRIPT = os.path.join(PROJECT_ROOT, "Model_ML", "predict.py")

def predict_sentiment(text: str) -> int:
	if not text or not text.strip():
		return 1
	if not os.path.isfile(PREDICT_SCRIPT):
		return 1

	# Try common python executables
	candidates = ["python3", "python"]
	for exe in candidates:
		try:
			out = subprocess.check_output(
				[exe, PREDICT_SCRIPT, text],
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
		except Exception:
			continue
	return 1


