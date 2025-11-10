import os
import json
from typing import Any, Dict, Optional, Tuple

import requests

SUPABASE_REST_URL = os.getenv("SUPABASE_REST_URL", "https://acddbjalchiruigappqg.supabase.co/rest/v1")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFjZGRiamFsY2hpcnVpZ2FwcHFnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTkwMzAzMTQsImV4cCI6MjA3NDYwNjMxNH0.Psefs-9-zIwe8OjhjQOpA19MddU3T9YMcfFtMcYQQS4")
SUPABASE_STORAGE_URL = os.getenv("SUPABASE_STORAGE_URL", "https://acddbjalchiruigappqg.supabase.co/storage/v1")

def supabase_request(method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, body: Optional[Dict[str, Any]] = None) -> Tuple[bool, int, Any, str]:
    url = f"{SUPABASE_REST_URL}/{endpoint.lstrip('/')}"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }
    # request representation back on write ops
    if method.upper() in {"POST", "PATCH", "PUT"}:
        headers["Prefer"] = "return=representation"

    try:
        resp = requests.request(method.upper(), url, params=params, data=json.dumps(body) if body is not None else None, headers=headers, timeout=30)
    except requests.RequestException as e:
        return True, 0, None, str(e)

    if resp.status_code >= 400:
        try:
            payload = resp.json()
        except ValueError:
            payload = None
        msg = payload.get("message") if isinstance(payload, dict) else f"HTTP Error: {resp.status_code}"
        return True, resp.status_code, payload, msg or f"HTTP Error: {resp.status_code}"

    try:
        data = resp.json()
    except ValueError:
        data = None
    return False, resp.status_code, data, ""

def supabase_storage_upload(bucket: str, file_name: str, file_bytes: bytes) -> Tuple[bool, Optional[str], str]:
    # POST /object/{bucket}/{path}
    encoded_bucket = requests.utils.quote(bucket, safe="")
    encoded_path = requests.utils.quote(file_name, safe="")
    url = f"{SUPABASE_STORAGE_URL}/object/{encoded_bucket}/{encoded_path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/octet-stream",
        "x-upsert": "true",
    }
    try:
        resp = requests.post(url, data=file_bytes, headers=headers, timeout=60)
    except requests.RequestException as e:
        return True, None, str(e)

    if resp.status_code >= 400:
        try:
            payload = resp.json()
            msg = payload.get("message", "")
        except ValueError:
            msg = ""
        return True, None, f"HTTP Error: {resp.status_code} - {msg}"

    # Public URL path
    return False, f"{bucket}/{file_name}", ""


