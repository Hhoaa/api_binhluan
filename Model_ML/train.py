import sys
import json
import re
import unicodedata
import torch
import torch.nn as nn

# ========== NORMALIZE ==========
def strip_accents(s: str) -> str:
    s = unicodedata.normalize('NFD', s)
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    return unicodedata.normalize('NFC', s)

def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = strip_accents(text)
    replacements = {"ko": "khong", "k": "khong", "hok": "khong", "dc": "duoc", "đc": "duoc", "oke": "ok"}
    for k, v in replacements.items():
        text = re.sub(r'\b' + re.escape(k) + r'\b', v, text)
    return text

# ========== LOAD MODEL ==========
try:
    vocab = json.load(open("vocab.json"))
    vocab_size = len(vocab) + 1
except:
    vocab = {}
    vocab_size = 1

class FastModel(nn.Module):
    def __init__(self, vocab_size):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, 128)
        self.lstm = nn.LSTM(128, 128, 1, batch_first=True, bidirectional=True)
        self.fc = nn.Linear(256, 2)
        self.dropout = nn.Dropout(0.2)
    
    def forward(self, x):
        x = self.embedding(x)
        _, (h, _) = self.lstm(x)
        h = torch.cat((h[0], h[1]), dim=1)
        return self.fc(self.dropout(h))

model = None
try:
    model = FastModel(vocab_size)
    model.load_state_dict(torch.load("vicloabsa_model_fast.pth", map_location="cpu"))
    model.eval()
except:
    model = None

# ========== NEGATION LEXICONS ==========
negation_words = {'khong', 'ko', 'k', 'hok', 'chua', 'chang', 'cha'}

positive_words = {'dep', 'tot', 're', 'xinh', 'ngon', 'chat', 'chuan', 'ok', 'on', 'ung'}
negative_words = {'te', 'xau', 'kem', 'toi', 'loi', 'rach', 'cu', 'hong', 'tệ', 'xấu'}
weak_negative_words = {'mong', 'mỏng'}

# ========== MAIN PREDICT ==========
def predict(text: str) -> int:
    # ✅ RULE #1: NHƯNG = 1 (ƯU TIÊN CAO NHẤT)
    if 'nhung' in text.lower() or 'nhưng' in text.lower():
        return 1
    
    norm = normalize_text(text)
    words = norm.split()
    
    # ✅ RULE #2: NEGATION LOGIC (Phủ định + từ → FLIP)
    for i, word in enumerate(words):
        # NEGATION + POSITIVE → NEGATIVE (0)
        if word in positive_words:
            prev_window = words[max(0, i-3):i]
            if any(neg in prev_window for neg in negation_words):
                return 0
        
        # NEGATION + NEGATIVE → POSITIVE (1)
        if word in negative_words | weak_negative_words:
            prev_window = words[max(0, i-3):i]
            if any(neg in prev_window for neg in negation_words):
                return 1
    
    # ✅ RULE #3: EXPLICIT NEGATIVE PHRASES = 0
    explicit_neg = [
        'khong dang tien', 'khong dang', 'mong qua', 'mỏng qua', 
        'te qua', 'xau qua', 'rat te', 'rat xau'
    ]
    for phrase in explicit_neg:
        if phrase in norm:
            return 0
    
    # ✅ RULE #4: STRONG NEGATIVE WORDS = 0
    if any(w in negative_words for w in words):
        return 0
    
    # ✅ RULE #5: WEAK NEGATIVE (mỏng/mong)
    has_weak_neg = any(w in weak_negative_words for w in words)
    if has_weak_neg:
        has_pos_context = any(w in {'ok', 'dc', 'duoc', 'tot', 'dep', 're'} for w in words)
        return 1 if has_pos_context else 0
    
    # ✅ FALLBACK: MODEL hoặc DEFAULT = 1
    if model is None:
        return 1
    else:
        tokens = [vocab.get(w, 0) for w in norm.split()][:64]
        tokens += [0] * (64 - len(tokens))
        with torch.no_grad():
            x = torch.tensor([tokens])
            outputs = model(x)
            pred = torch.argmax(outputs, 1).item()
            return pred

# ========== MAIN ==========
text = sys.argv[1] if len(sys.argv) > 1 else input()
print(predict(text))