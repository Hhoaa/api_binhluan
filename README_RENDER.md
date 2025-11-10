Deploy to Render (Web Service)

- Root: set to this `py_api` folder.
- Runtime: Python 3.11+
- Build Command:

  ```
  pip install -r requirements.txt
  ```

- Start Command:

  ```
  uvicorn app:app --host 0.0.0.0 --port $PORT
  ```

Environment Variables

- SUPABASE_REST_URL: https://acddbjalchiruigappqg.supabase.co/rest/v1
- SUPABASE_STORAGE_URL: https://acddbjalchiruigappqg.supabase.co/storage/v1
- SUPABASE_ANON_KEY: your anon key
- SUPABASE_PUBLIC_BASE: https://acddbjalchiruigappqg.supabase.co/storage/v1/object/public

Endpoints

- POST /add_review (JSON)
- POST /add_review_form (multipart/form-data)

Examples

```bash
curl -X POST "$RENDER_URL/add_review" \
  -H "Content-Type: application/json" \
  -d '{
    "ma_san_pham": 2,
    "ma_nguoi_dung": 54,
    "noi_dung_danh_gia": "Sản phẩm bị rách...",
    "diem_danh_gia": 1,
    "duong_dan_anh": ["https://example.com/a.jpg"]
  }'
```


