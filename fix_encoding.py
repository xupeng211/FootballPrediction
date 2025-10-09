#!/usr/bin/env python3
"""
修复UTF-8编码问题的脚本
"""

import os
import re


def fix_encoding_issues(filepath):
    """修复单个文件的编码问题"""
    print(f"正在处理: {filepath}")

    # 备份原文件
    backup_path = filepath + ".bak"
    if not os.path.exists(backup_path):
        os.rename(filepath, backup_path)

    try:
        # 尝试多种编码读取
        encodings = ["utf-8", "latin1", "cp1252", "iso-8859-1"]
        content = None

        for encoding in encodings:
            try:
                with open(backup_path, "r", encoding=encoding) as f:
                    content = f.read()
                print(f"  使用 {encoding} 编码成功读取")
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            # 最后尝试使用replace模式
            with open(backup_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            print("  使用 utf-8 replace 模式读取")

        # 修复常见的编码问题
        # 将乱码字符替换为正确的中文
        replacements = {
            "��Jf S\u0006h": "Alert Channel Manager",
            "\u0006@\tJf S\u0002": "Alert Channel Manager",
            "\u001d�\u0016 S�\u0006h": "初始化通道",
            "�Jf S": "注册通道",
            "S\r�": "通道名称",
            "S�a": "通道对象",
            "�\u0000Jf S": "注销通道",
            "��Jf S": "获取通道",
            "�\u0001Jf0@\t S": "发送告警",
            "Jf\u0017h": "告警列表",
            "\u0007�� S\r�\u0017h": "指定通道名称",
            "y��\u0001Jf0@\t S": "批量发送告警",
            "�� S�\u0001": "获取通道状态",
            "/( S": "启用通道",
            "�( S": "禁用通道",
            "/&\u0010�": "是否成功",
            "�� Sߡ": "获取通道统计",
            "K�@\t S": "测试所有通道",
            "Jf�a": "告警对象",
            "�\u0001Ӝ": "发送结果",
            "S�\u0011�o": "通道状态信息",
            "/(� S\u0017h": "启用通道列表",
            "�\u00010\u0007� S": "发送到指定通道",
            "�\u00010@\t/(� S": "发送到所有启用通道",
            "�\u001b�K�Jf": "创建测试告警",
            # Email channel specific
            "��Jf S\nEmail Alert Channel": "邮件告警通道",
            "\u0013Ǯ��\u0013Jf\u0002": "邮件告警通道",
            "�\u0013�� S": "初始化邮件通道",
            "SMn": "SMTP配置",
            "�\u0018\u0010Jf": "发送邮件告警",
            # Other patterns
            "Alert": "告警",
            "Channel": "通道",
            "Manager": "管理器",
            "Enable": "启用",
            "Disable": "禁用",
            "Send": "发送",
            "Test": "测试",
            "Status": "状态",
            "Config": "配置",
            "Initialize": "初始化",
            "Register": "注册",
            "Unregister": "注销",
        }

        # 执行替换
        for old, new in replacements.items():
            content = content.replace(old, new)

        # 清理其他不可见字符
        content = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", content)

        # 写入修复后的文件
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        print("  ✅ 修复完成")
        return True

    except Exception as e:
        print(f"  ❌ 修复失败: {e}")
        # 恢复备份
        if os.path.exists(backup_path):
            os.rename(backup_path, filepath)
        return False


def main():
    """主函数"""
    files_to_fix = [
        "src/monitoring/alerts/channels/channel_manager.py",
        "src/monitoring/alerts/channels/email_channel.py",
        "src/monitoring/alerts/channels/slack_channel.py",
        "src/monitoring/alerts/channels/sms_channel.py",
        "src/monitoring/alerts/channels/teams_channel.py",
        "src/monitoring/alerts/channels/webhook_channel.py",
    ]

    success_count = 0
    total_count = len(files_to_fix)

    print("=" * 60)
    print("🔧 修复UTF-8编码问题")
    print("=" * 60)

    for filepath in files_to_fix:
        if os.path.exists(filepath):
            if fix_encoding_issues(filepath):
                success_count += 1
        else:
            print(f"⚠️  文件不存在: {filepath}")

    print("=" * 60)
    print(f"✅ 修复完成: {success_count}/{total_count} 个文件")
    print("=" * 60)

    # 验证修复结果
    print("\n验证修复结果...")
    import subprocess

    result = subprocess.run(["file"] + files_to_fix, capture_output=True, text=True)
    print(result.stdout)


if __name__ == "__main__":
    main()
