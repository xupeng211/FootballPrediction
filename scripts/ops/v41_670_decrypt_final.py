#!/usr/bin/env python3
"""V41.670 最终解密测试 - 使用新提取的密钥."""

import base64
import hashlib
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# V41.670 新提取的密钥
NEW_PASSWORD = b"1354255sbicjR!p$7aD_commongHn*3brawLd_k"
NEW_SALT = b"5b9adecrypt3e6ddata7c8e9d0f180091rjhVYpmap"

# 测试数据 (ajax-all-events 响应)
ENCRYPTED_RESPONSE = "bHdaQUJPRzZVNEsrbEFvalRCKzRJSlhocDhUNDVNZlNTblgxL3dNZWdDUDR5cW1rT2RhMHdVRHE0UEsvRGNwRWtib3ZwNmRoUmZGdU9XRm4ydnpWWEE0T2ZuVmhPelgwNDZCZmplcEtrZTRKSHFKcy81Wm5QV2dIQWRBemFXSWQzSnEzRkQ4NlJwMWEwY3BBTFJmUFViOVZ4Zk1jR0xJKytDeGNhNjhSMDhpOFkvR3psWm12YWJCZmlRRU9YcEthNDYrYng2N2hidTJJUTl0T0paY2hlbUdJZVVSVUppMzFWclhzSloxQWhwV24rZWRqQjdNZ3hrdUdmaVlpcUV1c1hITkpiNjlVTTFzcTRrQk03cmowcXc0WnFhT0NvRHQyWjhlcDlDb1BwdERsZ3A4OGZSNGVQUm0vZHJQa1J6bTZKNml2cS93bTRZTE1Uci9XbEF6ZEI3bEFmVCtMeEZkb3B2a21XRW9KWkthbjJmRHZNZ2gwVVBNUzlyL3F4WXRQWWFRYnNYVEF5blEyYktVOTRJUFI1bWV2Y3YzMUdXRE8rcHlocGdhcjl0eTh3TkxvWnhzbzgvcW8zRWwwSXFBUUFncTVtU3N3V2o1emh3WldFVGwrUVdVSmlqeVFiOHVpYWhDVFVCTXZjQmlJYU9KRlRabmNXTmFOdmhiQ1dENVdNbWhLWmIzTmtsY0syZGI1U2FRTnJUSUZBN2c2MzNmeGpZYnkwdFlya2FCVno2d3pnTkw0V3I5VFRBYkJ1UU94dXY4WGZXdC9aNzVYbkVSVW4rU1JRMjhMb0VzbzdzMVZOOUZ0TTFKL2Z0bkN5MjY4eXovSkZtMHNpWTI5cVBHYm5YUW9hSVVyQmY4dUMvb3VJb1hubTRNd2pPUnhhaERpUHJDckdWRFhUR1lYbHQ3K21jaHZTOVVCd0tqKzZBcnRldXZPNStFNVFWWkN5VWxZWVVrU21nOW5DUzZSb3p3NUtQR2Vya01VaUQ1Mms1VEtFQlVjOWxwd2M4eEhGMmNvcDUvVWZUK0d3OEszaHZ1VTl3TUU2UURnY29IajBVQ2tKVG9vUlI1Qm1aQmtzdHYzNzI2WngrWnpYVHl2WEZUM0VobVBhMDhLcHNkTjVRT0x6alpWRHdadzJuemlXSXBIbFNpRVhuV0FFeVRienViRHJSb2crdTkzbVk3VUtBd1pxQnM3Q3ZJSURucmpjSXE4NWxaWEcvZXJ6NTFwMWhXZFRiR3FsNGNQVDJQTkEyb1U1bVNCbnE1QlVTc3ExWFNsVHBiajRPa2tCNlRVd2xrTUppYzlBT1IwVVo4U1R6TnlzeXZFVGRtK3ZGc2Z0TDYrYUFZYi9IMXFnSEJseXBMK1RPanNaZzhQbEhlNnRZM08vSkt2VkV2eHlKbkhFY2czYjlURUx5ZjdyVmw0Z0ZaR0tsU2F2aUI4ekkxZy9QVWRvRW0yRFZZRDRqaCsrWUQvTzhlaHRnaVdPNTlXUTZvbWdPampRWjIwSGkvVForNUNGSGF3QUhyU2RlaUhNTkE2MzlHdUM1TGs0Sm4wcnVhZEN4L2VPb1hnZVVPbTJmTTFWV1BHSWttVXJkMUNNdXhZUk1qay9DdGROendESmZ1aEx3cWV3UDZzUk9ac2RscmMweEtZTFFUSHozUjJVUDd1anI3Y1p4VDhQVDl4cmlPbjIzaGpVRXhTWlg5SmZkZzRlNTZBTWlRMGxEUThYcEV1NWFLYXo0WVhUbVRZeGdEU0p0ZFN0L1RFK3N5K0M3TzJXeWZrN2tkMVd5WFllbVBwWER1QVo3MC95WFF2c0Y5TDFnU2h4aFdFS3p3anVWMjFzS1FZQ2cvSDNJbGg2SUJ2QStLSHVML2NwY0h3OFlVMXp6Uk55RkQ4clZNVE9aUHg2ajNJQVBvZTZ5N296ZmM1VWo5ZGlOMXd1ZkRJRWhSTFV2TkhZTTJpZERwaW8zVGlnUFAxUEd2V2VUL0s5ckxka1haV094NFFQdGhBMUF0dVAzRVFnVnJpMHMxY2JZUForWlQ5VEE1ZitWcVhQY0JFaU92S0szQXJVS2JPMGp5Yk5RZnRZeGFBTTMzUG9SZWllQXNWYjdqYmV2S2VFbE8yaENpT244YlZBMWx5K0xHVWwwMjBaU0VYd3R0MDJZbWFQQ2V3cHhqb29IU1EyZEROVVRiYkkrWjFZQ3ZQQVZ2YWtROUtqeCtaQjdwYXl2aldxUUE4SXVKYStyZVNnd1Q0Mm9aVHlOay82TjRWaHJWR3ZvNGV4dmwzOWFicjhrcjN5QTVoTXRTOWxMWTF2RlM4SDd2TzBtYUh6d0dCSlVUcU83b1ZCOElkYUgwOG94dEhaU0ZpWUxiOUR2L3JJQk1lVzlPckNWQzF15eHBXa3dtbVNXMXBsS3l3VHpEWGxwRUwvNG5Kc1IzcW9oRGhGVjJGSjdBYUJITFJqZjQ1d3IzRXhvemV0ZkdhNUJSMlpycTBhTzFnZUVER0lTajhhOUtHek5MTkhWT1ZYaXQ3UW54ZEJKVmoxMVVRaDJ3PTpjMzc5NzNjNTA5ZDkyMTU0NjIzOTMyMTJkZTg5NDhhZg=="

def decrypt_oddsportal(encrypted_response: str, password: bytes, salt: bytes) -> str:
    """解密 OddsPortal 响应."""

    # Step 1: Base64 解码
    decoded_bytes = base64.b64decode(encrypted_response)

    # Step 2: 查找冒号分隔符
    colon_pos = decoded_bytes.find(b':')
    if colon_pos == -1:
        raise ValueError("未找到冒号分隔符")

    encrypted_part = decoded_bytes[:colon_pos]
    iv_hex = decoded_bytes[colon_pos + 1:].decode('ascii')

    # Step 3: 解码加密数据和 IV
    encrypted_data = base64.urlsafe_b64decode(encrypted_part)
    iv_bytes = bytes.fromhex(iv_hex)

    print(f"加密数据: {len(encrypted_data)} 字节")
    print(f"IV: {iv_hex} ({len(iv_bytes)} 字节)")

    # Step 4: PBKDF2 密钥派生
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 256 bits
        salt=salt,
        iterations=1000,
        backend=default_backend(),
    )
    key = kdf.derive(password)

    print(f"派生密钥 (hex): {key.hex()}")

    # Step 5: AES-256-CBC 解密
    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv_bytes),
        backend=default_backend(),
    )
    decryptor = cipher.decryptor()
    decrypted_padded = decryptor.update(encrypted_data) + decryptor.finalize()

    # Step 6: 移除 PKCS7 填充
    padding_length = decrypted_padded[-1]
    decrypted = decrypted_padded[:-padding_length]

    return decrypted.decode('utf-8')


def main():
    print("=" * 60)
    print("V41.670 解密测试 - 新密钥")
    print("=" * 60)
    print(f"\n密码: {NEW_PASSWORD.decode()}")
    print(f"盐值: {NEW_SALT.decode()}")

    try:
        result = decrypt_oddsportal(ENCRYPTED_RESPONSE, NEW_PASSWORD, NEW_SALT)

        print("\n" + "=" * 60)
        print("解密成功!")
        print("=" * 60)

        # 显示前 500 字符
        print(f"\n解密结果 (前 500 字符):")
        print("-" * 60)
        print(result[:500])

        # 检查是否包含 JSON 结构
        if '{' in result and '}' in result:
            print("\n" + "-" * 60)
            print("包含 JSON 结构 - 尝试解析...")

            import json
            try:
                data = json.loads(result)
                print(f"JSON 解析成功!")
                print(f"顶层键: {list(data.keys())}")

                # 查找比赛 ID
                if 'data' in data:
                    print(f"\ndata 键内容: {list(data['data'].keys())}")
            except json.JSONDecodeError as e:
                print(f"JSON 解析失败: {e}")

    except Exception as e:
        print(f"\n解密失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
