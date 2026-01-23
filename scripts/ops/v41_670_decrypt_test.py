#!/usr/bin/env python3
"""V41.670 解密测试 - 尝试不同参数组合."""

import base64
import hashlib
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# 测试数据
ENCRYPTED_RESPONSE = "bHdaQUJPRzZVNEsrbEFvalRCKzRJSlhocDhUNDVNZlNTblgxL3dNZWdDUDR5cW1rT2RhMHdVRHE0UEsvRGNwRWtib3ZwNmRoUmZGdU9XRm4ydnpWWEE0T2ZuVmhPelgwNDZCZmplcEtrZTRKSHFKcy81Wm5QV2dIQWRBemFXSWQzSnEzRkQ4NlJwMWEwY3BBTFJmUFViOVZ4Zk1jR0xJKytDeGNhNjhSMDhpOFkvR3psWm12YWJCZmlRRU9YcEthNDYrYng2N2hidTJJUTl0T0paY2hlbUdJZVVSVUppMzFWclhzSloxQWhwV24rZWRqQjdNZ3hrdUdmaVlpcUV1c1hITkpiNjlVTTFzcTRrQk03cmowcXc0WnFhT0NvRHQyWjhlcDlDb1BwdERsZ3A4OGZSNGVQUm0vZHJQa1J6bTZKNml2cS93bTRZTE1Uci9XbEF6ZEI3bEFmVCtMeEZkb3B2a21XRW9KWkthbjJmRHZNZ2gwVVBNUzlyL3F4WXRQWWFRYnNYVEF5blEyYktVOTRJUFI1bWV2Y3YzMUdXRE8rcHlocGdhcjl0eTh3TkxvWnhzbzgvcW8zRWwwSXFBUUFncTVtU3N3V2o1emh3WldFVGwrUVdVSmlqeVFiOHVpYWhDVFVCTXZjQmlJYU9KRlRabmNXTmFOdmhiQ1dENVdNbWhLWmIzTmtsY0syZGI1U2FRTnJUSUZBN2c2MzNmeGpZYnkwdFlya2FCVno2d3pnTkw0V3I5VFRBYkJ1UU94dXY4WGZXdC9aNzVYbkVSVW4rU1JRMjhMb0VzbzdzMVZOOUZ0TTFKL2Z0bkN5MjY4eXovSkZtMHNpWTI5cVBHYm5YUW9hSVVyQmY4dUMvb3VJb1hubTRNd2pPUnhhaERpUHJDckdWRFhUR1lYbHQ3K21jaHZTOVVCd0tqKzZBcnRldXZPNStFNVFWWkN5VWxZWVVrU21nOW5DUzZSb3p3NUtQR2Vya01VaUQ1Mms1VEtFQlVjOWxwd2M4eEhGMmNvcDUvVWZUK0d3OEszaHZ1VTl3TUU2UURnY29IajBVQ2tKVG9vUlI1Qm1aQmtzdHYzNzI2WngrWnpYVHl2WEZUM0VobVBhMDhLcHNkTjVRT0x6alpWRHdadzJuemlXSXBIbFNpRVhuV0FFeVRienViRHJSb2crdTkzbVk3VUtBd1pxQnM3Q3ZJSURucmpjSXE4NWxaWEcvZXJ6NTFwMWhXZFRiR3FsNGNQVDJQTkEyb1U1bVNCbnE1QlVTc3ExWFNsVHBiajRPa2tCNlRVd2xrTUppYzlBT1IwVVo4U1R6TnlzeXZFVGRtK3ZGc2Z0TDYrYUFZYi9IMXFnSEJseXBMK1RPanNaZzhQbEhlNnRZM08vSkt2VkV2eHlKbkhFY2czYjlURUx5ZjdyVmw0Z0ZaR0tsU2F2aUI4ekkxZy9QVWRvRW0yRFZZRDRqaWMrWUQvTzhlaHRnaVdPNTlXUTZvbWdPampRWjIwSGkvVForNUNGSGF3QUhyU2RlaUhNTkE2MzlHdUM1TGs0Sm4wcnVhZEN4L2VPb1hnZVVPbTJmTTFWV1BHSWttVXJkMUNNdXhZUk1qay9DdGROendESmZ1aEx3cWV3UDZzUk9ac2RscmMweEtZTFFUSHozUjJVUDd1anI3Y1p4VDhQVDl4cmlPbjIzaGpVRXhTWlg5SmZkZzRlNTZBTWlRMGxEUThYcEV1NWFLYXo0WVhUbVRZeGdEU0p0ZFN0L1RFK3N5K0M3TzJXeWZrN2tkMVd5WFllbVBwWER1QVo3MC95WFF2c0Y5TDFnU2h4aFdFS3p3anVWMjFzS1FZQ2cvSDNJbGg2SUJ2QStLSHVML2NwY0h3OFlVMXp6Uk55RkQ4clZNVE9aUHg2ajNJQVBvZTZ5N296ZmM1VWo5ZGlOMXd1ZkRJRWhSTFV2TkhZTTJpZERwaW8zVGlnUFAxUEd2V2VUL0s5ckxka1haV094NFFQdGhBMUF0dVAzRVFnVnJpMHMxY2JZUForWlQ5VEE1ZitWcVhQY0JFaU92S0szQXJVS2JPMGp5Yk5RZnRZeGFBTTMzUG9SZWllQXNWYjdqYmV2S2VFbE8yaENpT244YlZBMWx5K0xHVWwwMjBaU0VYd3R0MDJZbWFQQ2V3cHhqb29IU1EyZEROVVRiYkkrWjFZQ3ZQQVZ2YWtROUtqeCtaQjdwYXl2aldxUUE4SXVKYStyZVNnd1Q0Mm9aVHlOay82TjRWaHJWR3ZvNGV4dmwzOWFicjhrcjN5QTVoTXRTOWxMWTF2RlM4SDd2TzBtYUh6d0dCSlVUcU83b1ZCOElkYUgwOG94dEhaU0ZpWUxiOUR2L3JJQk1lVzlPckNWQzF5eHBXa3dtbVNXMXBsS3l3VHpEWGxwRUwvNG5Kc1IzcW9oRGhGVjJGSjdBYUJITFJqZjQ1d3IzRXhvemV0ZkdhNUJSMlpycTBhTzFnZUVER0lTajhhOUtHek5MTkhWT1ZYaXQ3UW54ZEJKVmoxMVVRaDJ3PTpjMjc5NzNjNTA5ZDkyMTU0NjIzOTMyMTJkZTg5NDhhZg=="

# 旧凭据（从 Stack Overflow 2024/12）
OLD_PASSWORD = b"%RtR8AB&\\nWsh=AQC+v!=pgAe@dSQG3kQ"
OLD_SALT = b"orieC_jQQWRmhkPvR6u2kzXeTube6aYupiOddsPortal"

print("V41.670 解密测试")
print("=" * 60)

# Step 1: Base64 解码
decoded_data = base64.b64decode(ENCRYPTED_RESPONSE).decode('utf-8')
print(f"Step 1: Base64 解码成功，长度: {len(decoded_data)}")

# Step 2: 分离加密数据和 IV
if ':' not in decoded_data:
    print("ERROR: 未找到冒号分隔符")
    exit(1)

encrypted_part, iv_hex = decoded_data.split(':', 1)
print(f"Step 2: 分离成功")
print(f"  加密数据长度: {len(encrypted_part)}")
print(f"  IV (hex): {iv_hex}")
print(f"  IV 长度: {len(iv_hex)} 字符 = {len(iv_hex)//2} 字节")

# Step 3: 解码加密数据和 IV
try:
    encrypted_bytes = base64.urlsafe_b64decode(encrypted_part)
    iv = bytes.fromhex(iv_hex)
    print(f"Step 3: 二进制解码成功")
    print(f"  加密数据: {len(encrypted_bytes)} 字节")
    print(f"  IV: {len(iv)} 字节")
except Exception as e:
    print(f"ERROR: 二进制解码失败: {e}")
    exit(1)

# Step 4: 尝试不同的密钥长度
test_configs = [
    ("AES-128-CBC (旧密码)", 16, OLD_PASSWORD, OLD_SALT, 1000),
    ("AES-256-CBC (旧密码)", 32, OLD_PASSWORD, OLD_SALT, 1000),
    ("AES-128-CBC (SHA256)", 16, b"test_password", b"test_salt", 1000),
    ("AES-256-CBC (直接IV)", 32, b"test_password", b"test_salt", 1000),
]

for name, key_len, password, salt, iterations in test_configs:
    print(f"\n测试: {name}")
    print("-" * 60)

    try:
        # 派生密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=key_len,
            salt=salt,
            iterations=iterations,
            backend=default_backend(),
        )
        key = kdf.derive(password)

        # 尝试解密
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(encrypted_bytes) + decryptor.finalize()

        # 尝试解码为 UTF-8
        try:
            text = decrypted.decode('utf-8')
            print(f"  ✓ 解密成功！")
            print(f"  前 200 字符: {text[:200]}")

            # 检查是否包含 JSON
            if '{' in text or '}' in text:
                print(f"  ✓ 包含 JSON 结构！")
                break
        except UnicodeDecodeError:
            print(f"  ✗ UTF-8 解码失败")
            # 显示十六进制
            hex_preview = decrypted[:50].hex()
            print(f"  十六进制预览: {hex_preview}")

    except Exception as e:
        print(f"  ✗ 解密失败: {e}")

print("\n" + "=" * 60)
print("测试完成")
