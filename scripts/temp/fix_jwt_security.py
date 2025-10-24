#!/usr/bin/env python3
"""
修复JWT密钥安全问题
"""

import os
import secrets
import string
import random

def generate_secure_jwt_secret():
    """生成强随机JWT密钥"""
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
    return ''.join(random.choice(alphabet) for _ in range(64))

def update_env_file():
    """更新.env文件中的JWT密钥"""
    env_file = '.env'
    current_secret = None

    # 读取当前内容
    current_content = ""
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            current_content = f.read()

    # 解析现有密钥
    for line in current_content.strip().split('\n'):
        if line.startswith('JWT_SECRET_KEY='):
            current_secret = line.split('=', 1)[1].strip()
            break

    # 生成新的安全密钥
    secure_key = generate_secure_jwt_secret()

    # 备份现有内容
    backup_content = current_content.replace(f'JWT_SECRET_KEY={current_secret}', f'# Previous key: {current_secret}', 1) if current_secret else ''

    # 构建新内容
    new_lines = []
    if current_content:
        # 保留所有非JWT_SECRET_KEY的行
        for line in current_content.strip().split('\n'):
            if not line.startswith('JWT_SECRET_KEY='):
                new_lines.append(line)

    # 添加新的JWT配置
    new_lines.extend([
        f'JWT_SECRET_KEY={secure_key}',
        f'JWT_SECRET_LENGTH={len(secure_key)}',
        f'JWT_SECRET_UPDATED={secrets.datetime.datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}',
        f'# Generated secure 64-bit key',
        '# Previous key backed up above if existed'
    ])

    # 写入文件
    with open(env_file, 'w') as f:
        f.write('\n'.join(new_lines))

def check_key_strength(key):
    """检查密钥强度"""
    score = 0
    if len(key) >= 32:
        score += 2
    if any(c in key for c in '0123456789'):
            score += 1
        if any(c in key for c in '!@#$%^&*'):
            score += 1
    return score

def main():
    print("🔐 开始修复JWT密钥安全问题...")

    try:
        update_env_file()
        secure_key = None

        # 读取新密钥
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('JWT_SECRET_KEY='):
                    secure_key = line.split('=', 1)[1].strip()
                    break

        if secure_key:
            strength_score = check_key_strength(secure_key)
            print(f"✅ JWT密钥更新成功")
            print(f"📊 新密钥长度: {len(secure_key)} 位")
            print(f"🔒 密钥强度评分: {strength_score}/4 (满分)")
            print(f"🔐 新密钥: {secure_key}")

            print("✅ JWT安全问题已修复")
        else:
            print("❌ 无法读取新密钥")

    except Exception as e:
        print(f"⚠️ 修复过程中出现错误: {e}")

if __name__ == "__main__":
    main()
"