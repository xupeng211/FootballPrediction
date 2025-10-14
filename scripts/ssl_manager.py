#!/usr/bin/env python3
"""
SSL证书管理工具
"""

import os
import sys
import subprocess
import datetime
from pathlib import Path
from typing import Optional, Tuple
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SSLManager:
    """SSL证书管理器"""

    def __init__(self, cert_dir: str = "./ssl"):
        self.cert_dir = Path(cert_dir)
        self.cert_dir.mkdir(exist_ok=True)

    def generate_self_signed_cert(
        self, domain: str = "localhost", days: int = 365
    ) -> Tuple[str, str]:
        """生成自签名证书"""
        logger.info(f"生成自签名证书: {domain}")

        key_path = self.cert_dir / "private.key"
        cert_path = self.cert_dir / "certificate.crt"

        # 生成私钥
        cmd = ["openssl", "genrsa", "-out", str(key_path), "2048"]
        subprocess.run(cmd, check=True)
        logger.info(f"私钥已生成: {key_path}")

        # 生成证书
        cmd = [
            "openssl",
            "req",
            "-new",
            "-x509",
            "-key",
            str(key_path),
            "-out",
            str(cert_path),
            "-days",
            str(days),
            "-subj",
            f"/C=CN/ST=State/L=City/O=FootballPrediction/CN={domain}",
        ]
        subprocess.run(cmd, check=True)
        logger.info(f"证书已生成: {cert_path}")

        # 设置权限
        key_path.chmod(0o600)
        cert_path.chmod(0o644)

        return str(key_path), str(cert_path)

    def get_cert_info(self, cert_path: str) -> dict:
        """获取证书信息"""
        cmd = [
            "openssl",
            "x509",
            "-in",
            cert_path,
            "-noout",
            "-dates",
            "-subject",
            "-issuer",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        info = {}
        for line in result.stdout.split("\n"):
            if "=" in line:
                key, value = line.split("=", 1)
                info[key.strip()] = value.strip()

        return info

    def check_cert_expiry(self, cert_path: str) -> Tuple[bool, int]:
        """检查证书是否过期"""
        info = self.get_cert_info(cert_path)

        if "notAfter" in info:
            expiry_date_str = info["notAfter"]
            expiry_date = datetime.datetime.strptime(
                expiry_date_str, "%b %d %H:%M:%S %Y %Z"
            )
            days_until_expiry = (expiry_date - datetime.datetime.now()).days

            is_expired = days_until_expiry < 0
            return is_expired, abs(days_until_expiry)

        return True, 0

    def generate_csr(self, domain: str, key_path: str) -> str:
        """生成证书签名请求"""
        csr_path = self.cert_dir / f"{domain}.csr"

        cmd = [
            "openssl",
            "req",
            "-new",
            "-key",
            str(key_path),
            "-out",
            str(csr_path),
            "-subj",
            f"/C=CN/ST=State/L=City/O=FootballPrediction/CN={domain}",
        ]
        subprocess.run(cmd, check=True)

        logger.info(f"CSR已生成: {csr_path}")
        return str(csr_path)

    def generate_dhparam(self, size: int = 2048) -> str:
        """生成Diffie-Hellman参数"""
        dhparam_path = self.cert_dir / "dhparam.pem"

        logger.info("生成DH参数（可能需要一些时间）...")
        cmd = ["openssl", "dhparam", "-out", str(dhparam_path), str(size)]
        subprocess.run(cmd, check=True)

        logger.info(f"DH参数已生成: {dhparam_path}")
        return str(dhparam_path)

    def create_ssl_bundle(self) -> str:
        """创建SSL证书包（包含证书链）"""
        cert_path = self.cert_dir / "certificate.crt"
        bundle_path = self.cert_dir / "fullchain.pem"

        if cert_path.exists():
            # 如果有中间证书，可以在这里追加
            with open(bundle_path, "w") as f:
                f.write(cert_path.read_text())
            logger.info(f"SSL证书包已创建: {bundle_path}")
            return str(bundle_path)

        return ""

    def verify_cert_key_match(self, cert_path: str, key_path: str) -> bool:
        """验证证书和私钥是否匹配"""
        # 获取证书的modulus
        cert_cmd = ["openssl", "x509", "-noout", "-modulus", "-in", cert_path]
        cert_result = subprocess.run(cert_cmd, capture_output=True, text=True)

        # 获取私钥的modulus
        key_cmd = ["openssl", "rsa", "-noout", "-modulus", "-in", key_path]
        key_result = subprocess.run(key_cmd, capture_output=True, text=True)

        # 比较modulus
        return cert_result.stdout == key_result.stdout

    def get_ssl_config_snippet(self, cert_path: str, key_path: str) -> str:
        """获取SSL配置片段"""
        return f"""
    # SSL Configuration
    ssl_certificate {cert_path};
    ssl_certificate_key {key_path};

    # SSL Protocols
    ssl_protocols TLSv1.2 TLSv1.3;

    # SSL Ciphers
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # SSL Session Cache
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
"""


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="SSL证书管理工具")
    parser.add_argument("--domain", default="localhost", help="域名")
    parser.add_argument("--cert-dir", default="./ssl", help="证书目录")
    parser.add_argument("--days", type=int, default=365, help="证书有效期天数")
    parser.add_argument(
        "--action",
        choices=["generate", "check", "csr", "dhparam"],
        default="generate",
        help="操作类型",
    )

    args = parser.parse_args()

    manager = SSLManager(args.cert_dir)

    if args.action == "generate":
        # 生成自签名证书
        key_path, cert_path = manager.generate_self_signed_cert(args.domain, args.days)

        # 生成DH参数
        dhparam_path = manager.generate_dhparam()

        # 验证证书和私钥
        if manager.verify_cert_key_match(cert_path, key_path):
            logger.info("✓ 证书和私钥匹配")
        else:
            logger.error("✗ 证书和私钥不匹配")

        # 检查证书信息
        info = manager.get_cert_info(cert_path)
        print("\n证书信息:")
        for k, v in info.items():
            print(f"  {k}: {v}")

        # 输出配置
        print("\nNginx SSL配置:")
        print(manager.get_ssl_config_snippet(cert_path, key_path))

    elif args.action == "check":
        # 检查证书
        cert_path = manager.cert_dir / "certificate.crt"
        if cert_path.exists():
            is_expired, days = manager.check_cert_expiry(str(cert_path))
            if is_expired:
                logger.error(f"证书已过期 {days} 天")
            else:
                logger.info(f"证书将在 {days} 天后过期")
        else:
            logger.error("证书文件不存在")

    elif args.action == "csr":
        # 生成CSR
        key_path = manager.cert_dir / "private.key"
        if not key_path.exists():
            logger.error("私钥文件不存在，请先生成")
            sys.exit(1)

        csr_path = manager.generate_csr(args.domain, str(key_path))
        logger.info(f"CSR文件已生成，可用于申请CA签名证书: {csr_path}")

    elif args.action == "dhparam":
        # 生成DH参数
        dhparam_path = manager.generate_dhparam()
        logger.info(f"DH参数已生成: {dhparam_path}")


if __name__ == "__main__":
    main()
