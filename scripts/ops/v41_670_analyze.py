#!/usr/bin/env python3
"""V41.670 加密数据分析."""

import base64

# 加密响应
ENCRYPTED = "bHdaQUJPRzZVNEsrbEFvalRCKzRJSlhocDhUNDVNZlNTblgxL3dNZWdDUDR5cW1rT2RhMHdVRHE0UEsvRGNwRWtib3ZwNmRoUmZGdU9XRm4ydnpWWEE0T2ZuVmhPelgwNDZCZmplcEtrZTRKSHFKcy81Wm5QV2dIQWRBemFXSWQzSnEzRkQ4NlJwMWEwY3BBTFJmUFViOVZ4Zk1jR0xJKytDeGNhNjhSMDhpOFkvR3psWm12YWJCZmlRRU9YcEthNDYrYng2N2hidTJJUTl0T0paY2hlbUdJZVVSVUppMzFWclhzSloxQWhwV24rZWRqQjdNZ3hrdUdmaVlpcUV1c1hITkpiNjlVTTFzcTRrQk03cmowcXc0WnFhT0NvRHQyWjhlcDlDb1BwdERsZ3A4OGZSNGVQUm0vZHJQa1J6bTZKNml2cS93bTRZTE1Uci9XbEF6ZEI3bEFmVCtMeEZkb3B2a21XRW9KWkthbjJmRHZNZ2gwVVBNUzlyL3F4WXRQWWFRYnNYVEF5blEyYktVOTRJUFI1bWV2Y3YzMUdXRE8rcHlocGdhcjl0eTh3TkxvWnhzbzgvcW8zRWwwSXFBUUFncTVtU3N3V2o1emh3WldFVGwrUVdVSmlqeVFiOHVpYWhDVFVCTXZjQmlJYU9KRlRabmNXTmFOdmhiQ1dENVdNbWhLWmIzTmtsY0syZGI1U2FRTnJUSUZBN2c2MzNmeGpZYnkwdFlya2FCVno2d3pnTkw0V3I5VFRBYkJ1UU94dXY4WGZXdC9aNzVYbkVSVW4rU1JRMjhMb0VzbzdzMVZOOUZ0TTFKL2Z0bkN5MjY4eXovSkZtMHNpWTI5cVBHYm5YUW9hSVVyQmY4dUMvb3VJb1hubTRNd2pPUnhhaERpUHJDckdWRFhUR1lYbHQ3K21jaHZTOVVCd0tqKzZBcnRldXZPNStFNVFWWkN5VWxZWVVrU21nOW5DUzZSb3p3NUtQR2Vya01VaUQ1Mms1VEtFQlVjOWxwd2M4eEhGMmNvcDUvVWZUK0d3OEszaHZ1VTl3TUU2UURnY29IajBVQ2tKVG9vUlI1Qm1aQmtzdHYzNzI2WngrWnpYVHl2WEZUM0VobVBhMDhLcHNkTjVRT0x6alpWRHdadzJuemlXSXBIbFNpRVhuV0FFeVRienViRHJSb2crdTkzbVk3VUtBd1pxQnM3Q3ZJSURucmpjSXE4NWxaWEcvZXJ6NTFwMWhXZFRiR3FsNGNQVDJQTkEyb1U1bVNCbnE1QlVTc3ExWFNsVHBiajRPa2tCNlRVd2xrTUppYzlBT1IwVVo4U1R6TnlzeXZFVGRtK3ZGc2Z0TDYrYUFZYi9IMXfnSEJseXBMK1RPanNaZzhQbEhlNnRZM08vSkt2VkV2eHlKbkhFY2czYjlURUx5ZjdyVmw0Z0ZaR0tsU2F2aUI4ekkxZy9QVWRvRW0yRFZZRDRqaWMrWUQvTzhlaHRnaVdPNTlXUTZvbWdPampRWjIwSGkvVForNUNGSGF3QUhyU2RlaUhNTkE2MzlHdUM1TGs0Sm4wcnVhZEN4L2VPb1hnZVVPbTJmTTFWV1BHSWttVXJkMUNNdXhZUk1qay9DdGROendESmZ1aEx3cWV3UDZzUk9ac2RscmMweEtZTFFUSHozUjJVUDd1anI3Y1p4VDhQVDl4cmlPbjIzaGpVRXhTWlg5SmZkZzRlNTZBTWlRMGxEUThYcEV1NWFLYXo0WVhUbVRZeGdEU0p0ZFN0L1RFK3N5K0M3TzJXeWZrN2tkMVd5WFllbVBwWER1QVo3MC95WFF2c0Y5TDFnU2h4aFdFS3p3anVWMjFzS1FZQ2cvSDNJbGg2SUJ2QStLSHVML2NwY0h3OFlVMXp6Uk55RkQ4clZNVE9aUHg2ajNJQVBvZTZ5N296ZmM1VWo5ZGlOMXd1ZkRJRWhSTFV2TkhZTTJpZERwaW8zVGlnUFAxUEd2V2VUL0s5ckxka1haV094NFFQdGhBMUF0dVAzRVFnVnJpMHMxY2JZUForWlQ5VEE1ZitWcVhQY0JFaU92S0szQXJVS2JPMGp5Yk5RZnRZeGFBTTMzUG9SZWllQXNWYjdqYmV2S2VFbE8yaENpT244YlZBMWx5K0xHVWwwMjBaU0VYd3R0MDJZbWFQQ2V3cHhqb29IU1EyZEROVVRiYkkrWjFZQ3ZQQVZ2YWtROUtqeCtaQjdwYXl2aldxUUE4SXVKYStyZVNnd1Q0Mm9aVHlOay82TjRWaHJWR3ZvNGV4dmwzOWFicjhrcjN5QTVoTXRTOWxMWTF2RlM4SDd2TzBtYUh6d0dCSlVUcU83b1ZCOElkYUgwOG94dEhaU0ZpWUxiOUR2L3JJQk1lVzlPckNWQzF15eHBXa3dtbVNXMXBsS3l3VHpEWGxwRUwvNG5Kc1IzcW9oRGhGVjJGSjdBYUJITFJqZjQ1d3IzRXhvemV0ZkdhNUJSMlpycTBhTzFnZUVER0lTajhhOUtHek5MTkhWT1ZYaXQ3UW54ZEJKVmoxMVVRaDJ3PTpjMjc5NzNjNTA5ZDkyMTU0NjIzOTMyMTJkZTg5NDhhZg=="

# Base64 解码
decoded_bytes = base64.b64decode(ENCRYPTED)
decoded = decoded_bytes.decode('utf-8', errors='replace')

# 分离
parts = decoded.split(':')
encrypted_part = parts[0]
iv_hex = parts[1]

print('=== 数据格式分析 ===')
print(f'完整长度: {len(decoded)}')
print(f'加密数据: {len(encrypted_part)} 字符')
print(f'IV (hex): {iv_hex} ({len(iv_hex)} 字符 = {len(iv_hex)//2} 字节)')

# Base64 解码加密数据
encrypted_bytes = base64.urlsafe_b64decode(encrypted_part)

print(f'\n=== 加密数据分析 ===')
print(f'长度: {len(encrypted_bytes)} 字节')
print(f'前 32 字节 (hex): {encrypted_bytes[:32].hex()}')
print(f'IV (hex): {iv_hex}')

# 检查前 16 字节是否与 IV 相关
iv_bytes = bytes.fromhex(iv_hex)
print(f'\nIV 字节: {iv_bytes.hex()}')

# 尝试简单 XOR 解密 (假设 IV 既是 IV 也是密钥)
xor_result = bytes(a ^ b for a, b in zip(encrypted_bytes[:64], iv_bytes * 4))
print(f'\nXOR with IV (前 64 字节):')
print(f'Hex: {xor_result.hex()}')
try:
    print(f'Text: {xor_result.decode("utf-8", errors="ignore")}')
except:
    pass

# 检查块大小
print(f'\n=== 块分析 ===')
print(f'数据长度: {len(encrypted_bytes)} 字节')
print(f'可能块大小: 16 (AES-128) 或 32 (AES-256)')
print(f'是否整除 16: {len(encrypted_bytes) % 16 == 0}')
print(f'是否整除 32: {len(encrypted_bytes) % 32 == 0}')

# 寻找重复模式
print(f'\n=== 重复字节分析 ===')
from collections import Counter
byte_counts = Counter(encrypted_bytes)
top_10 = byte_counts.most_common(10)
print(f'最常见的 10 个字节: {[(hex(b), c) for b, c in top_10]}')
