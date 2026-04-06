"""
数据验证工具函数单元测试
"""
import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.auth_api import validate_phone, validate_email


class TestPhoneValidation:
    """手机号验证测试"""
    
    def test_valid_phone_numbers(self):
        """测试有效的手机号"""
        valid_phones = [
            "13800138000",
            "13912345678",
            "15012345678",
            "18612345678",
            "19912345678"
        ]
        for phone in valid_phones:
            assert validate_phone(phone) is True, f"{phone} 应该是有效的手机号"
    
    def test_invalid_phone_numbers(self):
        """测试无效的手机号"""
        invalid_phones = [
            "12345678901",  # 不是1开头
            "1380013800",   # 少于11位
            "138001380001", # 多于11位
            "abc12345678",  # 包含字母
            "138-0013-8000", # 包含特殊字符
            "",             # 空字符串
            "23800138000",  # 第二位不是3-9
        ]
        for phone in invalid_phones:
            assert validate_phone(phone) is False, f"{phone} 应该是无效的手机号"
    
    def test_phone_edge_cases(self):
        """测试边界情况"""
        assert validate_phone(None) is False
        assert validate_phone("1380013800a") is False


class TestEmailValidation:
    """邮箱验证测试"""
    
    def test_valid_emails(self):
        """测试有效的邮箱"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.org",
            "user+tag@gmail.com",
            "user_123@test.cn",
            "admin@company.co.uk"
        ]
        for email in valid_emails:
            assert validate_email(email) is True, f"{email} 应该是有效的邮箱"
    
    def test_invalid_emails(self):
        """测试无效的邮箱"""
        invalid_emails = [
            "not-an-email",
            "@example.com",       # 缺少用户名
            "user@",              # 缺少域名
            "user@.com",          # 域名不完整
            "user@example",       # 缺少顶级域名
            "user @example.com",  # 包含空格
            "",                   # 空字符串
        ]
        for email in invalid_emails:
            assert validate_email(email) is False, f"{email} 应该是无效的邮箱"
    
    def test_email_edge_cases(self):
        """测试边界情况"""
        assert validate_email(None) is False


class TestDataTypes:
    """数据类型验证测试"""
    
    def test_validate_phone_returns_boolean(self):
        """验证返回类型是布尔值"""
        result = validate_phone("13800138000")
        assert isinstance(result, bool)
    
    def test_validate_email_returns_boolean(self):
        """验证返回类型是布尔值"""
        result = validate_email("test@example.com")
        assert isinstance(result, bool)
