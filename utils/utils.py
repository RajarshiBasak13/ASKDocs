from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt

# ===== UTILS =====
SECRET_KEY = 'your_secret_key_your_secret_key_'
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALLOWED_EXTENSIONS = {"pdf", "txt"}


def hash_password(password):
    return pwd_context.hash(password)


def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)


def create_token(email):
    payload = {
        "sub": email,
        "exp": datetime.utcnow() + timedelta(days=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def allowed_file(file):
    name = file.filename
    file.stream.seek(0, 2)  # move to end
    size = file.stream.tell()  # get size
    file.stream.seek(0)  # reset pointer

    return "." in file.filename and \
        file.filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS and size < 1 * 1024 * 1024