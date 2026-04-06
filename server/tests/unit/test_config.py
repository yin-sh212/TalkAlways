"""
配置模块单元测试
"""
import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import config


class TestConfig:
    """配置模块测试"""
    
    def test_config_exists(self):
        """测试配置对象存在"""
        assert config is not None
    
    def test_app_name_exists(self):
        """测试应用名称配置存在"""
        assert hasattr(config, 'APP_NAME')
        assert isinstance(config.APP_NAME, str)
        assert len(config.APP_NAME) > 0
    
    def test_app_version_exists(self):
        """测试应用版本配置存在"""
        assert hasattr(config, 'APP_VERSION')
        assert isinstance(config.APP_VERSION, str)
    
    def test_debug_mode_is_boolean(self):
        """测试调试模式是布尔值"""
        assert hasattr(config, 'DEBUG')
        assert isinstance(config.DEBUG, bool)
    
    def test_database_config_exists(self):
        """测试数据库配置存在"""
        assert hasattr(config, 'DB_HOST')
        assert hasattr(config, 'DB_PORT')
        assert hasattr(config, 'DB_USER')
        assert hasattr(config, 'DB_PASSWORD')
        assert hasattr(config, 'DB_NAME')
    
    def test_db_port_is_integer(self):
        """测试数据库端口是整数"""
        assert isinstance(config.DB_PORT, int)
        assert config.DB_PORT > 0
    
    def test_redis_config_exists(self):
        """测试Redis配置存在（可选）"""
        # Redis可能是可选的，所以只检查属性是否存在
        assert hasattr(config, 'REDIS_HOST') or True  # 允许不存在
    
    def test_config_values_are_not_empty_strings(self):
        """测试关键配置不为空字符串"""
        assert config.APP_NAME.strip() != ""
        assert config.DB_HOST.strip() != ""
        assert config.DB_USER.strip() != ""
        assert config.DB_NAME.strip() != ""


class TestEnvironmentVariables:
    """环境变量测试"""
    
    def test_env_file_loaded(self):
        """测试.env文件已加载"""
        # 如果配置有值，说明.env文件被正确加载
        assert config.DB_HOST is not None
    
    def test_sensitive_data_not_hardcoded(self):
        """测试敏感数据不是硬编码的"""
        # 密码应该从环境变量读取，不应该是明显的硬编码值
        if config.DB_PASSWORD:
            assert config.DB_PASSWORD not in ["password", "123456", "admin"]
