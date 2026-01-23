#!/usr/bin/env python3
"""V41.680 金丝雀实测 - 验证新密钥解密功能."""

import time
import logging
from src.core.oddsportal_decryptor import OddsPortalDecryptor

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# 测试数据 (从 V41.670 收集)
TEST_DATA = "bHdaQUJPRzZVNEsrbEFvalRCKzRJSlhocDhUNDVNZlNTblgxL3dNZWdDUDR5cW1rT2RhMHdVRHE0UEsvRGNwRWtib3ZwNmRoUmZGdU9XRm4ydnpWWEE0T2ZuVmhPelgwNDZCZmplcEtrZTRKSHFKcy81Wm5QV2dIQWRBemFXSWQzSnEzRkQ4NlJwMWEwY3BBTFJmUFViOVZ4Zk1jR0xJKytDeGNhNjhSMDhpOFkvR3psWm12YWJCZmlRRU9YcEthNDYrYng2N2hidTJJUTl0T0paY2hlbUdJZVVSVUppMzFWclhzSloxQWhwV24rZWRqQjdNZ3hrdUdmaVlpcUV1c1hITkpiNjlVTTFzcTRrQk03cmowcXc0WnFhT0NvRHQyWjhlcDlDb1BwdERsZ3A4OGZSNGVQUm0vZHJQa1J6bTZKNml2cS93bTRZTE1Uci9XbEF6ZEI3bEFmVCtMeEZkb3B2a21XRW9KWkthbjJmRHVNZ2gwVVBNUzlyL3F4WXRQWWFRYnNYVEF5blEyYktVOTRJUFI1bWV2Y3YzMUdXRE8rcHlocGdhcjl0eTh3TkxvWnhzbzgvcW8zRWwwSXFBUUFncTVtU3N3V2o1emh3WldFVGwrUVdVSmlqeVFiOHVpYWhDVFVCTXZjQmlJYU9KRlRabmNXTmFOdmhiQ1dENVdNbWhLWmIzTmtsY0syZGI1U2FRTnJUSUZBN2c2MzNmeGpZYnkwdFlya2FCVno2d3pnTkw0V3I5VFRBYkJ1UU94dXY4WGZXdC9aNzVYbkVSVW4rU1JRMjhMb0VzbzdzMVZOOUZ0TTFKL2Z0bkN5MjY4eXovSkZtMHNpWTI5cVBHYm5YUW9hSVVyQmY4dUMvb3VJb1hubTRNd2pPUnhhaERpUHJDckdWRFhUR1lYbHQ3K21jaHZTOVVCd0tqKzZBcnRldXZPNStFNVFWWkN5VWxZWVVrU21nOW5DUzZSb3p3NUtQR2Vya01VaUQ1Mms1VEtFQlVjOWxwd2M4eEhGMmNvcDUvVWZUK0d3OEszaHZ1VTl3TUU2UURnY29IajBVQ2tKVG9vUlI1Qm1aQmtzdHYzNzI2WngrWnpYVHl2WEZUM0VobVBhMDhLcHNkTjVRT0x6alpWRHdadzJuemlXSXBIbFNpRVhuV0FFeVRienViRHJSb2crdTkzbVk3VUtBd1pxQnM3Q3ZJSURucmpjSXE4NWxaWEcvZXJ2NTFwMWhXZFRiR3FsNGNQVDJQTkEyb1U1bVNCbnE1QlVTc3ExWFNsVHBiajRPa2tCNlRVd2xrTUppQzlBT1IwVVo4U1R6TnlzeXZFVGRtK3ZGc2Z0TDYrYUFZYi9IMXfnSEJseXBMK1RPanNaZzhQbEhlNnRZM08vSkt2VkV2eHlKbkhFY2czYjlURUx5ZjdyVmw0Z0ZaR0tsU2F2aUI4ekkxZy9QVWRvRW0yRFZZRDRqaCsrWUQvTzhlaHRnaVdPNTlXUTZvbWdPampRWjIwSGkvVForNUNGSGF3QUhyU2RlaUhNTkE2MzlHdUM1TGs0Sm4wcnVhZEN4L2VPb1hnZVVPbTJmTTFWV1BHSWttVXJkMUNNdXhZUk1qay9DdGROendESmZ1aEx3cWV3UDZzUk9ac2RscmMweEtZTFFUSHozUjJVUDd1anI3Y1p4VDhQVDl4cmlPbjIzaGpVRXhTWlg5SmZkZzRlNTZBTWlRMGxEUThYcEV1NWFLYXo0WVhUbVRZeGdEU0p0ZFN0L1RFK3N5K0M3TzJXeWZrN2tkMVd5WFllbVBwWER1QVo3MC95WFF2c0Y5TDFnU2h4aFdFS3p3anVWMjFzS1FZQ2cvSDNJbGg2SUJ2QStLSHVML2NwY0h3OFlVMXp6Uk55RkQ4clZNVE9aUHg2ajNJQVBvZTZ5N296ZmM1VWo5ZGlOMXd1ZkRJRWhSTFV2TkhZTTJpZERwaW8zVGlnUFAxUEd2V2VUL0s5ckxka1haV094NFFQdGhBMUF0dVAzRVFnVnJpMHMxY2JZUForWlQ5VEE1ZitWcVhQY0JFaU92S0szQXJVS2JPMGp5Yk5RZnRZeGFBTTMzUG9SZWllQXNWYjdqYmV2S2VFbE8yaENpT244YlZBMWx5K0xHVWwwMjBaU0VYd3R0MDJZbWFQQ2V3cHhqb29IU1EyZEROVVRiYkkrWjFZQ3ZQQVZ2YWtROUtqeCtaQjdwYXl2aldxUUE4SXVKYStyZVNnd1Q0Mm9aVHlOay82TjRWaHJWR3ZvNGV4dmwzOWFicjhrcjN5QTVoTXRTOWxMWTF2RlM4SDd2TzBtYUh6d0dCSlVUcU83b1ZCOElkYUgwOG94dEhaU0ZpWUxiOUR2L3JJQk1lVzlPckNWQzF15eHBXa3dtbVNXMXBsS3l3VHpEWGxwRUwvNG5Kc1IzcW9oRGhGVjJGSjdBYUJITFJqZjQ1d3IzRXhvemV0ZkdhNUJSMlpycTBhTzFnZUVER0lTajhhOUtHek5MTkhWT1ZYaXQ3UW54ZEJKVmoxMVVRaDJ3PTpjMzc5NzNjNTA5ZDkyMTU0NjIzOTMyMTJkZTg5NDhhZg=="


def main():
    """运行金丝雀解密测试."""
    print("=" * 70)
    print("V41.680 金丝雀实测 - 新密钥解密验证")
    print("=" * 70)

    # 显示当前密钥配置
    decryptor = OddsPortalDecryptor()
    print(f"\n当前密钥配置:")
    print(f"  密码长度: {len(decryptor.password)} 字符")
    print(f"  密码预览: {decryptor.password[:10]}...{decryptor.password[-10:]}")
    print(f"  盐值长度: {len(decryptor.salt)} 字符")
    print(f"  盐值预览: {decryptor.salt[:10]}...{decryptor.salt[-10:]}")

    # 运行解密测试
    print(f"\n开始解密测试...")
    print("-" * 70)

    start_time = time.time()
    result = decryptor.decrypt_feed(TEST_DATA)
    elapsed = (time.time() - start_time) * 1000  # 转换为毫秒

    if result:
        print(f"\n✓ 解密成功!")
        print(f"  延迟: {elapsed:.2f} ms")
        print(f"  数据字段数: {len(result) if isinstance(result, dict) else 'N/A'}")

        # 显示前 500 字符
        print(f"\n解密内容预览 (前 500 字符):")
        print("-" * 70)
        if isinstance(result, dict):
            import json
            preview = json.dumps(result, indent=2, ensure_ascii=False)[:500]
            print(preview)
            if len(preview) >= 500:
                print("...")

            # 检查关键数据
            print(f"\n关键数据检查:")
            print(f"  顶层键: {list(result.keys())[:10]}")

            # 查找比赛相关数据
            if 'data' in result:
                data = result['data']
                if isinstance(data, dict):
                    print(f"  data 键: {list(data.keys())[:10]}")
        else:
            print(str(result)[:500])

        # 验收标准检查
        print(f"\n{'=' * 70}")
        print("验收标准:")
        print(f"  ✓ 解密延迟 < 100ms: {'PASS' if elapsed < 100 else 'FAIL'} ({elapsed:.2f} ms)")
        print(f"  ✓ 包含有效数据: {'PASS' if result else 'FAIL'}")
        print(f"{'=' * 70}")

        return True
    else:
        print(f"\n✗ 解密失败")
        print(f"  延迟: {elapsed:.2f} ms")
        print(f"\n可能原因:")
        print(f"  1. 测试数据格式不匹配")
        print(f"  2. 需要获取实时数据进行测试")
        print(f"  3. IV 提取方式需要调整")

        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
