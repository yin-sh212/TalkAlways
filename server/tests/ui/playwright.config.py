"""
Playwright测试配置
"""
from playwright.sync_api import Playwright, BrowserType


def pytest_configure(config):
    """Pytest配置钩子"""
    config.addinivalue_line(
        "markers", "ui: mark test as UI test requiring browser"
    )


# 默认浏览器配置
BROWSER = "chromium"
HEADLESS = True
VIEWPORT = {"width": 1920, "height": 1080}
BASE_URL = "http://localhost:8080"
