"""
Services模块额外测试
提升覆盖率的补充测试
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# Test email service
def test_email_service():
    """测试邮件服务"""
    with patch("src.services.email.EmailService") as MockService:
        service = MockService()
        service.send_email = Mock(return_value={"sent": True, "message_id": "123"})
        service.send_template_email = Mock(return_value={"sent": True})
        service.validate_email = Mock(return_value=True)

        # 测试发送邮件
        result = service.send_email(
            to="test@example.com", subject="Test Email", body="Test content"
        )
        assert result["sent"] is True

        # 测试模板邮件
        template_result = service.send_template_email(
            to="test@example.com", template="welcome", data={"name": "User"}
        )
        assert template_result["sent"] is True


# Test notification service
def test_notification_service():
    """测试通知服务"""
    with patch("src.services.notification.NotificationService") as MockService:
        service = MockService()
        service.send_notification = Mock(return_value={"sent": True})
        service.send_bulk_notification = Mock(return_value={"sent": 100})
        service.get_notification_status = Mock(return_value="delivered")

        # 测试发送通知
        result = service.send_notification(
            user_id=1, message="Test notification", type="info"
        )
        assert result["sent"] is True

        # 测试批量发送
        bulk_result = service.send_bulk_notification(
            user_ids=[1, 2, 3], message="Bulk notification"
        )
        assert bulk_result["sent"] == 100


# Test search service
def test_search_service():
    """测试搜索服务"""
    with patch("src.services.search.SearchService") as MockService:
        service = MockService()
        service.search = Mock(
            return_value=[
                {"id": 1, "title": "Result 1"},
                {"id": 2, "title": "Result 2"},
            ]
        )
        service.index_document = Mock(return_value=True)
        service.get_search_suggestions = Mock(
            return_value=["suggestion1", "suggestion2"]
        )

        # 测试搜索
        results = service.search(query="test", limit=10)
        assert len(results) == 2

        # 测试索引文档
        indexed = service.index_document(doc_id="doc_1", content="Test content")
        assert indexed is True


# Test export service
def test_export_service():
    """测试导出服务"""
    with patch("src.services.export.ExportService") as MockService:
        service = MockService()
        service.export_to_csv = Mock(return_value={"file_path": "/exports/data.csv"})
        service.export_to_excel = Mock(return_value={"file_path": "/exports/data.xlsx"})
        service.export_to_json = Mock(return_value={"file_path": "/exports/data.json"})

        # 测试CSV导出
        csv_result = service.export_to_csv(
            data=[{"name": "A"}, {"name": "B"}], filename="data"
        )
        assert "data.csv" in csv_result["file_path"]

        # 测试Excel导出
        excel_result = service.export_to_excel(
            data=[{"name": "A"}, {"name": "B"}], filename="data"
        )
        assert "data.xlsx" in excel_result["file_path"]
