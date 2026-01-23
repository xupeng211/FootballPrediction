#!/usr/bin/env python3
"""V41.670 加密数据分析 - 修复版."""

import base64

# 直接使用原始字节
encrypted_response = "bHdaQUJPRzZVNEsrbEFvalRCKzRJSlhocDhUNDVNZlNTblgxL3dNZWdDUDR5cW1rT2RhMHdVRHE0UEsvRGNwRWtib3ZwNmRoUmZGdU9XRm4ydnpWWEE0T2ZuVmhPelgwNDZCZmplcEtrZTRKSHFKcy81Wm5QV2dIQWRBemFXSWQzSnEzRkQ4NlJwMWEwY3BBTFJmUFViOVZ4Zk1jR0xJKytDeGNhNjhSMDhpOFkvR3psWm12YWJCZmlRRU9YcEthNDYrYng2N2hidTJJUTl0T0paY2hlbUdJZVVSVUppMzFWclhzSloxQWhwV24rZWRqQjdNZ3hrdUdmaVlpcUV1c1hITkpiNjlVTTFzcTRrQk03cmowcXc0WnFhT0NvRHQyWjhlcDlDb1BwdERsZ3A4OGZSNGVQUm0vZHJQa1J6bTZKNml2cS93bTRZTE1Uci9XbEF6ZEI3bEFmVCtMeEZkb3B2a21XRW9KWkthbjJmRHZNZ2gwVVBNUzlyL3F4WXRQWWFRYnNYVEF5blEyYktVOTRJUFI1bWV2Y3YzMUdXRE8rcHlocGdhcjl0eTh3TkxvWnhzbzgvcW8zRWwwSXFBUUFncTVtU3N3V2o1emh3WldFVGwrUVdVSmlqeVFiOHVpYWhDVFVCTXZjQmlJYU9KRlRabmNXTmFOdmhiQ1dENVdNbWhLWmIzTmtsY0syZGI1U2FRTnJUSUZBN2c2MzNmeGpZYnkwdFlya2FCVno2d3pnTkw0V3I5VFRBYkJ1UU94dXY4WGZXdC9aNzVYbkVSVW4rU1JRMjhMb0VzbzdzMVZOOUZ0TTFKL2Z0bkN5MjY4eXovSkZtMHNpWTI5cVBHYm5YUW9hSVVyQmY4dUMvb3VJb1hubTRNd2pPUnhhaERpUHJDckdWRFhUR1lYbHQ3K21jaHZTOVVCd0tqKzZBcnRldXZPNStFNVFWWkN5VWxZWVVrU21nOW5DUzZSb3p3NUtQR2Vya01VaUQ1Mms1VEtFQlVjOWxwd2M4eEhGMmNvcDUvVWZUK0d3OEszaHZ1VTl3TUU2UURnY29IajBVQ2tKVG9vUlI1Qm1aQmtzdHYzNzI2WngrWnpYVHl2WEZUM0VobVBhMDhLcHNkTjVRT0x6alpWRHdadzJuemlXSXBIbFNpRVhuV0FFeVRienViRHJSb2crdTkzbVk3VUtBd1pxQnM3Q3ZJSURucmpjSXE4NWxaWEcvZXJ6NTFwMWhXZFRiR3FsNGNQVDJQTkEyb1U1bVNCbnE1QlVTc3ExWFNsVHBiajRPa2tCNlRVd2xrTUppYzlBT1IwVVo4U1R6TnlzeXZFVGRtK3ZGc2Z0TDYrYUFZYi9IMXfnSEJseXBMK1RPanNaZzhQbEhlNnRZM08vSkt2VkV2eHlKbkhFY2czYjlURUx5ZjdyVmw0Z0ZaR0tsU2F2aUI4ekkxZy9QVWRvRW0yRFZZRDRqaWmrWUQvTzhlaHRnaVdPNTlXUTZvbWdPampRWjIwSGkvVForNUNGSGF3QUhyU2RlaUhNTkE2MzlHdUM1TGs0Sm4wcnVhZEN4L2VPb1hnZVVPbTJmTTFWV1BHSWttVXJkMUNNdXhZUk1qay9DdGROendESmZ1aEx3cWV3UDZzUk9ac2RscmMweEtZTFFUSHozUjJVUDd1anI3Y1p4VDhQVDl4cmlPbjIzaGpVRXhTWlg5SmZkZzRlNTZBTWlRMGxEUThYcEV1NWFLYXo0WVhUbVRZeGdEU0p0ZFN0L1RFK3N5K0M3TzJXeWZrN2tkMVd5WFllbVBwWER1QVo3MC95WFF2c0Y5TDFnU2h4aFdFS3p3anVWMjFzS1FZQ2cvSDNJbGg2SUJ2QStLSHVML2NwY0h3OFlVMXp6Uk55RkQ4clZNVE9aUHg2ajNJQVBvZTZ5N296ZmM1VWo5ZGlOMXd1ZkRJRWhSTFV2TkhZTTJpZERwaW8zVGlnUFAxUEd2V2VUL0s5ckxka1haV094NFFQdGhBMUF0dVAzRVFnVnJpMHMxY2JZUForWlQ5VEE1ZitWcVhQY0JFaU92S0szQXJVS2JPMGp5Yk5RZnRZeGFBTTMzUG9SZWllQXNWYjdqYmV2S2VFbE8yaENpT244YlZBMWx5K0xHVWwwMjBaU0VYd3R0MDJZbWFQQ2V3cHhqb29IU1EyZEROVVRiYkkrWjFZQ3ZQQVZ2YWtROUtqeCtaQjdwYXl2aldxUUE4SXVKYStyZVNnd1Q0Mm9aVHlOay82TjRWaHJWR3ZvNGV4dmwzOWFicjhrcjN5QTVoTXRTOWxMWTF2RlM4SDd2TzBtYUh6d0dCSlVUcU83b1ZCOElkYUgwOG94dEhaU0ZpWUxiOUR2L3JJQk1lVzlPckNWQzF15eHBXa3dtbVNXMXBsS3l3VHpEWGxwRUwvNG5Kc1IzcW9oRGhGVjJGSjdBYUJITFJqZjQ1d3IzRXhvemV0ZkdhNUJSMlpycTBhTzFnZUVER0lTajhhOUtHek5MTkhWT1ZYaXQ3UW54ZEJKVmoxMVVRaDJ3PTpjMzc5NzNjNTA5ZDkyMTU0NjIzOTMyMTJkZTg5NDhhZg=="

# Base64 解码
decoded_bytes = base64.b64decode(encrypted_response)

# 查找冒号位置
colon_pos = decoded_bytes.find(b':')

if colon_pos == -1:
    print("ERROR: 未找到冒号分隔符")
    exit(1)

encrypted_part = decoded_bytes[:colon_pos]
iv_hex = decoded_bytes[colon_pos + 1:].decode('ascii')

print('=== 数据格式分析 ===')
print(f'完整长度: {len(decoded_bytes)} 字节')
print(f'冒号位置: {colon_pos}')
print(f'加密数据: {len(encrypted_part)} 字节')
print(f'IV (hex): {iv_hex} ({len(iv_hex)} 字符 = {len(iv_hex)//2} 字节)')

# Base64 URL-safe 解码
encrypted_data = base64.urlsafe_b64decode(encrypted_part)

print(f'\n=== 加密数据分析 ===')
print(f'加密数据: {len(encrypted_data)} 字节')
print(f'前 32 字节 (hex): {encrypted_data[:32].hex()}')
print(f'IV: {iv_hex}')

# IV 字节
iv_bytes = bytes.fromhex(iv_hex)

print(f'\n=== XOR 解密尝试 ===')

# 简单 XOR 解密 (假设 IV 是密钥)
xor_result = bytes(a ^ b for a, b in zip(encrypted_data[:128], (iv_bytes * 8)))
print(f'XOR 结果 (前 128 字节):')
print(f'Hex: {xor_result.hex()[:100]}...')

# 尝试解码
try:
    text = xor_result.decode('utf-8', errors='ignore')
    if text.strip():
        print(f'Text: {text[:200]}')
except:
    pass

# 检查是否有可打印字符
print(f'\n=== 模式检测 ===')
print(f'数据长度: {len(encrypted_data)} 字节')
print(f'是否整除 16: {len(encrypted_data) % 16 == 0}')
print(f'是否整除 32: {len(encrypted_data) % 32 == 0}')

# 检查熵 (随机性)
from collections import Counter
byte_counts = Counter(encrypted_data[:256])
unique_bytes = len(byte_counts)
entropy_ratio = unique_bytes / len(encrypted_data[:256])
print(f'唯一字节比例 (前 256): {entropy_ratio:.3f}')
print(f'(1.0 = 完全随机, < 0.5 = 有模式)')

# 显示前几个字节
print(f'\n前 20 个字节: {list(encrypted_data[:20])}')
