import subprocess
import sys

# Danh sách test cases
test_cases = [
    "quá mỏng",
    "không như hình", 
    "sản phẩm không đẹp",
    "sản phẩm không quá tệ",
    "hơi mỏng nhưng ok",
    "Áo không quá mỏng",
    "Chưa đẹp lắm",
    "không đáng tiền",
    "không tệ",
    "không xấu",
    "không đắt",
    "tạm ổn",
    "cũng được",
    "đắt nhưng xứng đáng",
    "đẹp nhưng mỏng",
    "rất tệ",
    "cực kỳ đẹp",
    "vải mỏng",
    "áo đẹp",
    "sản phẩm bình thường",
    "rất đẹp",
    "quá xấu",
    "chưa tốt",
    "hàng lỗi",
    "đóng gói đẹp",
    "không hài lòng",
    "hơi dày",
    "chất lượng kém",
    "5 sao",
    "không xứng đáng",
    "tạm được"
]

print("🔥 TESTING 30 CASES...")
print("=" * 60)

passed = 0
total = len(test_cases)

for i, test_text in enumerate(test_cases, 1):
    try:
        result = subprocess.run([sys.executable, "predict.py", test_text], 
                              capture_output=True, text=True, timeout=5)
        output = result.stdout.strip()
        
        # Expected results (0=tiêu cực, 1=tích cực)
        expected = {
            "quá mỏng": 0,
            "không như hình": 0,
            "sản phẩm không đẹp": 0,
            "sản phẩm không quá tệ": 1,
            "hơi mỏng nhưng ok": 1,
            "Áo không quá mỏng": 1,
            "Chưa đẹp lắm": 0,
            "không đáng tiền": 0,
            "không tệ": 1,
            "không xấu": 1,
            "không đắt": 1,
            "tạm ổn": 1,
            "cũng được": 1,
            "đắt nhưng xứng đáng": 1,
            "đẹp nhưng mỏng": 0,
            "rất tệ": 0,
            "cực kỳ đẹp": 1,
            "vải mỏng": 0,
            "áo đẹp": 1,
            "sản phẩm bình thường": 1,
            "rất đẹp": 1,
            "quá xấu": 0,
            "chưa tốt": 0,
            "hàng lỗi": 0,
            "đóng gói đẹp": 1,
            "không hài lòng": 0,
            "hơi dày": 1,
            "chất lượng kém": 0,
            "5 sao": 1,
            "không xứng đáng": 0,
            "tạm được": 1
        }.get(test_text, 1)
        
        is_pass = output == str(expected)
        status = "✅ PASS" if is_pass else "❌ FAIL"
        passed += 1 if is_pass else 0
        
        print(f"{i:2d}. '{test_text}' → {output} | Expected: {expected} | {status}")
        
    except Exception as e:
        print(f"{i:2d}. '{test_text}' → ERROR: {e}")
    
    print()

print("=" * 60)
print(f"🎯 KẾT QUẢ: {passed}/{total} PASSED ({passed/total*100:.1f}%)")
if passed == total:
    print("🚀 HOÀN HẢO 100%!")
else:
    print("🔧 CẦN FIX!")