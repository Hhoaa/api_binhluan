import sys
import json
import re
import unicodedata
import torch
import torch.nn as nn

# ========== HÀM CHUẨN HÓA ==========
def strip_accents(s: str) -> str:
    s = unicodedata.normalize('NFD', s)
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    return unicodedata.normalize('NFC', s)

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    text = strip_accents(text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    # simple replacements / common typos
    replacements = {
        'đẹp':'dep', 'đep':'dep', 'tệ':'te', 'xấu':'xau', 'mỏng':'mong',
        'không':'khong', 'ko':'khong', 'k ':'khong ', 'chưa':'chua',
        'rất':'rat', 'quá':'qua', 'đắt':'dat', 'đáng':'dang',
        'hình':'hinh', 'hàng':'hang', 'lỗi':'loi', 'lỗi':'loi'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

# ========== LOAD VOCAB & MODEL (optional) ==========
vocab = {}
vocab_size = 1
model = None
try:
    vocab = json.load(open("vocab.json", encoding="utf-8"))
    vocab_size = len(vocab) + 1

    class FastModel(nn.Module):
        def __init__(self, vocab_size):
            super().__init__()
            self.embedding = nn.Embedding(vocab_size, 128)
            self.lstm = nn.LSTM(128, 128, batch_first=True, bidirectional=True)
            self.fc = nn.Linear(256, 2)
            self.dropout = nn.Dropout(0.2)
        def forward(self, x):
            x = self.embedding(x)
            _, (h, _) = self.lstm(x)
            if h.size(0) >= 2:
                h_cat = torch.cat((h[-2], h[-1]), dim=1)
            else:
                h_cat = h[-1]
            return self.fc(self.dropout(h_cat))

    model = FastModel(vocab_size)
    for fn in ["vicloabsa_model_fixed.pth"]:
        try:
            model.load_state_dict(torch.load(fn, map_location="cpu"))
            model.eval()
            break
        except Exception:
            pass
except Exception:
    model = None

# ========== RULE ENGINE (giữ theo style của bạn) ==========
def rule_predict(text: str) -> int:
    norm = normalize_text(text)
    words = norm.split()

    # ----- EXPLICIT NEGATIVE PHRASES (high priority) -----
    # Use regex so spacing/order/punctuation don't break matching
    explicit_negative_patterns = [
         r'\bkhong\s+nhu\s+hinh\b',        # không như hình
        r'\bkhong\s+giong\s+hinh\b',
        r'\bkhong\s+dang\s+tien\b',       # không đáng tiền
        r'\bkhong\s+xung\s+dang\b',       # không xứng đáng
        r'\bkhong\s+xungdang\b',          # khôngxứngđáng (dính từ)
        r'\bkhong\s+dang\b',  
         r'\bkhong\s+đang\b',             # không đáng (alone)
        r'\bkhong\s+xung\b',              # không xứng (alone)
        r'\bkhong\s+hai\s+long\b',        # không hài lòng
        r'\bkhong\s+giong\b',
        r'\bhang\s+loi\b',
        r'\bhang\s+bi\s+loi\b',
        r'\bchat\s+luong\s+(kem|thap)\b',
        r'\bchat\s+luong\s+kem\b',
        r'\bkhong\s+dep\b',
    ]
    for p in explicit_negative_patterns:
        if re.search(p, norm):
            return 0

    # ----- EXPLICIT POSITIVE PHRASES -----
    explicit_positive_patterns = [
        r'\bkhong\s+te\b', r'\bkhong\s+xau\b'
    ]
    for p in explicit_positive_patterns:
        if re.search(p, norm):
            return 1

    # ----- RULE: NHUNG => ưu tiên vế sau, nhưng vế sau có negative => negative
    if 'nhung' in words:
        left, right = norm.split('nhung', 1)
        left = left.strip(); right = right.strip()
        # Evaluate right first using simpler checks:
        # If right contains explicit negative pattern -> negative
        for p in explicit_negative_patterns:
            if re.search(p, right):
                return 0
        # If right contains positive phrase -> positive
        for p in explicit_positive_patterns:
            if re.search(p, right):
                return 1
        # If right contains any strong negative token -> negative
        if re.search(r'\b(mong|xau|te|kem|loi|rach|hong)\b', right):
            return 0
        # If right contains any positive token -> positive
        if re.search(r'\b(dep|tot|ok|on|re|dang|tuyet|5|5sao)\b', right):
            return 1
        # else, fallback to left check
        # left negative? then negative, left positive? then positive
        if re.search(r'\b(mong|xau|te|kem|loi|rach|hong)\b', left):
            return 0
        if re.search(r'\b(dep|tot|ok|on|re|dang|tuyet|5|5sao)\b', left):
            return 1
        # default per your policy: "nhung" => 1
        return 1

    # ----- RULE: 'chua + tot/dep' -> negative (explicit)
    if re.search(r'\bchua\s+(dep|tot|hai\s+long|on|duoc)\b', norm):
        return 0

    # ----- intensifier + negation handling: 'khong qua mong' -> positive
    # If pattern "khong (qua)? X" where X is negative -> invert -> positive
    if re.search(r'\bkhong\s+(qua\s+)?(mong|xau|te|kem|toi|khong)\b', norm):
        return 1

    # If intensifier without negation: 'rat/qua + mong/xau' -> negative
    if re.search(r'\b(rat|qua|cuc|cucky|cuc\s+ky)\s+(mong|xau|te|kem|toi)\b', norm):
        return 0
    # intensifier + positive -> positive
    if re.search(r'\b(rat|qua|cuc|cucky|cuc\s+ky)\s+(dep|tot|tuyet|xuat\s+sac)\b', norm):
        return 1

    # ----- weak explicit negatives (single tokens) -----
    if re.search(r'\b(mong|mongqua|mongqua|mong)\b', norm):
        # if there is positive context around like "mong nhưng ok/duoc" then positive
        if re.search(r'\b(mong).{0,20}\b(ok|duoc|on|dep|tot)\b', norm):
            return 1
        return 0

    # ----- explicit "hang loi" or 'chat luong kem' (some user's earlier fails) -----
    if re.search(r'\bhang\s+loi\b', norm) or re.search(r'\bchat\s+luong\s+kem\b', norm) or re.search(r'\bhang\s+bi\s+loi\b', norm):
        return 0

    # ----- 'khong hai long' variations -----
    if re.search(r'\bkhong\s+hai\s+long\b', norm) or re.search(r'\bkhong\s+hài\s+long\b', norm):
        return 0

    # ----- 'khong dep' or 'san pham khong dep' handled earlier but just in case:
    if re.search(r'\bkhong\s+dep\b', norm):
        return 0

    # ----- token-level scan with negation window (keeps your original spirit) -----
    # Build small lexicons (expandable)
    positive_words = ['dep','tot','ok','on','re','ung','hai','long','chat','xinh','tuyet','dang','5sao','5','sao']
    negative_words = ['te','xau','kem','mong','loi','rach','hong','toi','dat','thatvong','khongdang','khaox']
    negation_words = ['khong','chua','chang','cha']

    toks = norm.split()
    score = 0
    for i, w in enumerate(toks):
        base = 0
        if w in positive_words:
            base = 1
        elif w in negative_words:
            base = -1
        if base != 0:
            prev = toks[max(0, i-2):i]
            if any(n in prev for n in negation_words):
                base = -base
            score += base

    # If decisive by token scan
    if score > 0:
        return 1
    if score < 0:
        return 0

    # If still ambiguous -> fallback to model
    return -1

# ========== MODEL PREDICT (fallback) ==========
def model_predict(text: str) -> int:
    if model is None:
        return 1
    norm = normalize_text(text)
    toks = norm.split()
    token_ids = [vocab.get(t,0) for t in toks][:64]
    if len(token_ids) == 0:
        return 1
    if len(token_ids) < 64:
        token_ids += [0] * (64 - len(token_ids))
    x = torch.tensor([token_ids])
    with torch.no_grad():
        out = model(x)
        probs = torch.softmax(out, dim=1)
        pred = int(torch.argmax(out, dim=1).item())
        if float(probs.max()) < 0.6:
            return 1
        return pred

# ========== MAIN ==========
if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else input().strip()
    r = rule_predict(text)
    if r == -1:
        r = model_predict(text)
    print(r)
