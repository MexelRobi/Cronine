import os
import sys
import json
import base64
import math
from datetime import datetime
from llama_cpp import Llama
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

HOME_DIR = os.environ.get("HOME") or os.path.expanduser("~")
DB_PATH = os.path.join(HOME_DIR, ".cronine_db.json")
HASH_PATH = os.path.join(HOME_DIR, ".cronine_h")

_LLM_INSTANCE = None
_CRYPTO_KEY = None
_RAM_DATABASE = None

def get_llm():
    global _LLM_INSTANCE
    if _LLM_INSTANCE is None:
        try:
            _LLM_INSTANCE = Llama.from_pretrained(
                repo_id="Qwen/Qwen2.5-3B-Instruct-GGUF",
                filename="qwen2.5-3b-instruct-q4_k_m.gguf",
                verbose=False,
                n_ctx=4048,
                embedding=True
            )
        except Exception:
            sys.exit(1)
    return _LLM_INSTANCE

def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000
    )
    return kdf.derive(password.encode())

def hash_password(password: str) -> str:
    digest = hashes.Hash(hashes.SHA256())
    digest.update(password.encode())
    return base64.b64encode(digest.finalize()).decode()

def store_password_hash(password: str):
    h = hash_password(password)
    with open(HASH_PATH, "w", encoding="utf-8") as f:
        f.write(h)

def verify_password_input(password: str) -> bool:
    if not os.path.exists(HASH_PATH):
        return False
    with open(HASH_PATH, "r", encoding="utf-8") as f:
        stored = f.read().strip()
    return hash_password(password) == stored

def clear_password_hash():
    if os.path.exists(HASH_PATH):
        os.remove(HASH_PATH)

def set_encryption_password(password: str):
    global _CRYPTO_KEY
    salt = b"cronine_fixed_salt_16b"
    _CRYPTO_KEY = derive_key(password, salt)
    init_database_cache()

def clear_encryption_key():
    global _CRYPTO_KEY, _RAM_DATABASE
    _CRYPTO_KEY = None
    _RAM_DATABASE = {}

def is_db_encrypted() -> bool:
    return os.path.exists(HASH_PATH)

def encrypt_data(plaintext: str) -> str:
    if _CRYPTO_KEY is None:
        raise Exception("Database locked")
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(_CRYPTO_KEY), modes.CFB(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext.encode('utf-8')) + encryptor.finalize()
    return base64.b64encode(iv + ciphertext).decode('utf-8')

def decrypt_data(ciphertext_b64: str) -> str:
    if _CRYPTO_KEY is None:
        raise Exception("Database locked")
    raw = base64.b64decode(ciphertext_b64.encode('utf-8'))
    iv = raw[:16]
    ciphertext = raw[16:]
    cipher = Cipher(algorithms.AES(_CRYPTO_KEY), modes.CFB(iv))
    decryptor = cipher.decryptor()
    return (decryptor.update(ciphertext) + decryptor.finalize()).decode('utf-8')
def init_database_cache():
    global _RAM_DATABASE
    if not os.path.exists(DB_PATH):
        _RAM_DATABASE = {}
        return
    with open(DB_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if "encrypted" in data:
                if _CRYPTO_KEY is None:
                    _RAM_DATABASE = {}
                    return
                decrypted = decrypt_data(data["encrypted"])
                _RAM_DATABASE = json.loads(decrypted)
            else:
                _RAM_DATABASE = data
        except Exception:
            _RAM_DATABASE = {}

def load_db():
    global _RAM_DATABASE
    if _RAM_DATABASE is None:
        init_database_cache()
    if is_db_encrypted() and _CRYPTO_KEY is None:
        return {"error": "locked"}
    return _RAM_DATABASE

def save_db(data):
    global _RAM_DATABASE
    _RAM_DATABASE = data
    try:
        serialized = json.dumps(data, ensure_ascii=False, indent=4)
        if is_db_encrypted() and _CRYPTO_KEY is not None:
            encrypted_str = encrypt_data(serialized)
            payload = {"encrypted": encrypted_str}
        else:
            payload = data
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def save_entry(text, date_str=None):
    if not date_str or not date_str.strip():
        date_str = datetime.now().strftime("%Y-%m-%d")
    db = load_db()
    if "error" in db:
        return "error_locked"
    if date_str in db:
        if isinstance(db[date_str], list):
            db[date_str].append(text)
        else:
            db[date_str] = [db[date_str], text]
    else:
        db[date_str] = [text]
    save_db(db)
    return date_str

def delete_entry_by_index(date_str, index):
    db = load_db()
    if "error" in db:
        return
    if date_str in db:
        if isinstance(db[date_str], list):
            if 0 <= index < len(db[date_str]):
                db[date_str].pop(index)
                if not db[date_str]:
                    db.pop(date_str)
        else:
            db.pop(date_str)
        save_db(db)

def update_entry_by_index(date_str, index, new_text):
    db = load_db()
    if "error" in db:
        return
    if date_str in db:
        if isinstance(db[date_str], list):
            if 0 <= index < len(db[date_str]):
                db[date_str][index] = new_text
        else:
            db[date_str] = new_text
        save_db(db)

def get_vector_embedding(llm, text: str):
    try:
        res = llm.create_embedding(text)
        return res["data"][0]["embedding"]
    except Exception:
        return None

def calculate_similarity(v1, v2) -> float:
    if not v1 or not v2:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    m1 = math.sqrt(sum(a * a for a in v1))
    m2 = math.sqrt(sum(b * b for b in v2))
    if m1 == 0.0 or m2 == 0.0:
        return 0.0
    return dot / (m1 * m2)

def ask_cronine(query_text):
    try:
        llm = get_llm()
        db = load_db()
        if "error" in db:
            return "Database is encrypted. Please unlock first."
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        sorted_dates = sorted(list(db.keys()), reverse=True)
        recent_dates = sorted_dates[:3]
        
        query_vector = get_vector_embedding(llm, query_text)
        ranked_historical = []
        
        for d in sorted_dates:
            if d in recent_dates:
                continue
            day_content = json.dumps({d: db[d]}, ensure_ascii=False)
            day_vector = get_vector_embedding(llm, day_content)
            score = calculate_similarity(query_vector, day_vector)
            ranked_historical.append((score, d))
            
        ranked_historical.sort(key=lambda x: x[0], reverse=True)
        top_historical_dates = [d for _, d in ranked_historical[:5]]
        
        combined_db = {}
        for d in sorted_dates:
            if d in recent_dates or d in top_historical_dates:
                combined_db[d] = db[d]
                
        db_context = json.dumps(combined_db, ensure_ascii=False, indent=2)
        
        system_context = (
            "You are Cronine, a precise personal AI diary assistant backed by an injection RAG architecture. "
            f"The current date and time is strictly {current_timestamp}. Today is {today_str}. "
            "You see the most semantically relevant memories and the most recent days in the context. "
            "Analyze this context autonomously to answer the user's intent. "
            "Carefully distinguish between what happened 'today' vs what happened on previous dates. "
            "If the user asks about today and there is no entry for today's date in the context, explicitly say that nothing has been recorded yet for today. "
            "Always reply to the user in fluent, grammatically correct German based on their diary history. "
            "Never use technical terms such as JSON, database, dictionary, structure, index, embedding, or RAG. "
            "Ensure your response sentences are completely written out and never cut off mid-word."
        )
        user_prompt = f"User diary history:\n{db_context}\n\nQuestion: {query_text}"
        formatted_prompt = (
            f"<|im_start|>system\n{system_context}<|im_end|>\n"
            f"<|im_start|>user\n{user_prompt}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        
        output = llm(
            formatted_prompt,
            max_tokens=512,
            temperature=0.3,
            repeat_penalty=1.1,
            stop=["<|im_end|>", "<|im_start|>"],
            echo=False
        )
        
        if isinstance(output, dict) and "choices" in output:
            choices = output["choices"]
            if isinstance(choices, list) and len(choices) > 0:
                return choices[0]["text"].strip()
            elif isinstance(choices, dict) and "text" in choices:
                return choices["text"].strip()
                
        return str(output).strip()
    except Exception as e:
        return f"AI Error: {e}"

if not os.path.exists(HASH_PATH):
    init_database_cache()
