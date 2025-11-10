import io
import os
import time
from typing import List, Optional

import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from supabase_client import supabase_request, supabase_storage_upload
from sentiment import predict_sentiment

app = FastAPI(title="Zamy Shop API (Python)")

# CORS
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

SUPABASE_PUBLIC_BASE = os.getenv("SUPABASE_PUBLIC_BASE", "https://acddbjalchiruigappqg.supabase.co/storage/v1/object/public")

class AddReviewPayload(BaseModel):
	ma_san_pham: int
	ma_nguoi_dung: int
	noi_dung_danh_gia: str
	diem_danh_gia: Optional[int] = None
	ma_danh_gia_cha: Optional[int] = None
	duong_dan_anh: Optional[List[str] | str] = None

@app.get("/health")
def health():
	return {"ok": True}

@app.post("/add_review")
async def add_review_json(payload: Optional[AddReviewPayload] = None):
	"""
	JSON body version.
	"""
	if payload is None:
		raise HTTPException(status_code=400, detail="Missing JSON body")

	product_id = payload.ma_san_pham
	user_id = payload.ma_nguoi_dung
	comment = payload.noi_dung_danh_gia
	rating = payload.diem_danh_gia
	parent_review_id = payload.ma_danh_gia_cha
	image_urls_input = payload.duong_dan_anh

	if not product_id or not user_id or not comment:
		raise HTTPException(status_code=400, detail="Thiếu thông tin bắt buộc")

	# Predict sentiment using existing Model_ML/predict.py for parity with PHP
	status = 1 if parent_review_id else predict_sentiment(comment)

	review_data = {
		"ma_san_pham": int(product_id),
		"ma_nguoi_dung": int(user_id),
		"noi_dung_danh_gia": comment,
		"trang_thai": status,
		"thoi_gian_tao": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
		"thoi_gian_cap_nhat": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
	}
	if rating is not None:
		review_data["diem_danh_gia"] = int(rating)
	if parent_review_id is not None:
		review_data["ma_danh_gia_cha"] = int(parent_review_id)

	err, code, data, msg = supabase_request("POST", "reviews", {"select": "ma_danh_gia"}, review_data)
	if err:
		raise HTTPException(status_code=500, detail=f"Thêm đánh giá thất bại: {msg}")

	review_id = (data or [{}])[0].get("ma_danh_gia")
	if not review_id:
		raise HTTPException(status_code=500, detail="Không lấy được mã đánh giá")

	uploaded_images: List[str] = []

	if image_urls_input:
		urls = image_urls_input if isinstance(image_urls_input, list) else [image_urls_input]
		for idx, img_url in enumerate(urls):
			try:
				resp = requests.get(img_url, timeout=60)
				resp.raise_for_status()
			except requests.RequestException:
				continue
			content = resp.content
			ext = (os.path.splitext(img_url.split("?")[0])[1] or ".jpg").lstrip(".")
			new_name = f"reviews/review_{review_id}_{int(time.time())}_{idx}.{ext}"
			up_err, up_path, up_msg = supabase_storage_upload("review-images", new_name, content)
			if not up_err and up_path:
				public_url = f"{SUPABASE_PUBLIC_BASE}/{up_path}"
				uploaded_images.append(public_url)
				# Insert mapping
				supabase_request("POST", "review_images", {}, {
					"ma_danh_gia": review_id,
					"duong_dan_anh": public_url,
					"thoi_gian_tao": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
					"thoi_gian_cap_nhat": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
				})

	return {
		"error": False,
		"message": "Thêm đánh giá thành công",
		"ma_danh_gia": review_id,
		"anh_da_tai_len": uploaded_images,
	}

@app.post("/add_review_form")
async def add_review_form(
	ma_san_pham: int = Form(...),
	ma_nguoi_dung: int = Form(...),
	noi_dung_danh_gia: str = Form(...),
	diem_danh_gia: Optional[int] = Form(None),
	ma_danh_gia_cha: Optional[int] = Form(None),
	hinh_anh: Optional[List[UploadFile]] = None,
):
	"""
	multipart/form-data version with file uploads
	"""
	comment_payload = AddReviewPayload(
		ma_san_pham=ma_san_pham,
		ma_nguoi_dung=ma_nguoi_dung,
		noi_dung_danh_gia=noi_dung_danh_gia,
		diem_danh_gia=diem_danh_gia,
		ma_danh_gia_cha=ma_danh_gia_cha,
	)

	# Create review first
	resp = await add_review_json(comment_payload)
	review_id = resp["ma_danh_gia"]
	uploaded_images = resp["anh_da_tai_len"] or []

	# Upload images if provided
	if hinh_anh:
		for idx, file in enumerate(hinh_anh):
			content = await file.read()
			ext = (os.path.splitext(file.filename)[1] or ".jpg").lstrip(".")
			new_name = f"reviews/review_{review_id}_{int(time.time())}_{idx}.{ext}"
			up_err, up_path, up_msg = supabase_storage_upload("review-images", new_name, content)
			if not up_err and up_path:
				public_url = f"{SUPABASE_PUBLIC_BASE}/{up_path}"
				uploaded_images.append(public_url)
				supabase_request("POST", "review_images", {}, {
					"ma_danh_gia": review_id,
					"duong_dan_anh": public_url,
					"thoi_gian_tao": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
					"thoi_gian_cap_nhat": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
				})

	return {
		"error": False,
		"message": "Thêm đánh giá thành công",
		"ma_danh_gia": review_id,
		"anh_da_tai_len": uploaded_images,
	}

if __name__ == "__main__":
	import uvicorn
	uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))


