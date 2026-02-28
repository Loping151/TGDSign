"""塔吉多签名与加密工具"""

import hashlib
import base64
import uuid

from Crypto.Cipher import AES

SECRET = "89155cc4e8634ec5b1b6364013b23e3e"


def _pad(data: bytes) -> bytes:
    """PKCS5/PKCS7 填充"""
    pad_len = AES.block_size - (len(data) % AES.block_size)
    return data + bytes([pad_len] * pad_len)


def _encrypt_aes(plaintext: str, key: str) -> bytes:
    """AES ECB 加密"""
    key_bytes = key.encode("utf-8")
    plaintext_bytes = plaintext.encode("utf-8")
    padded = _pad(plaintext_bytes)
    cipher = AES.new(key_bytes, AES.MODE_ECB)
    return cipher.encrypt(padded)


def generate_sign(params: dict) -> str:
    """生成请求签名"""
    sorted_keys = sorted(params.keys())
    values_str = "".join([str(params[key]) for key in sorted_keys])
    sign_str = values_str + SECRET
    return hashlib.md5(sign_str.encode()).hexdigest()


def aes_base64_encode(plaintext: str) -> str:
    """AES 加密后 Base64 编码"""
    key = SECRET[-16:]
    encrypted = _encrypt_aes(plaintext, key)
    return base64.b64encode(encrypted).decode("utf-8")


def get_random_device_id() -> str:
    """生成随机设备ID"""
    return str(uuid.uuid4()).replace("-", "").lower()
