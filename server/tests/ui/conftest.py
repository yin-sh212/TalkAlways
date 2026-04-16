"""
UI测试全局配置和fixtures
"""
import pytest
from playwright.sync_api import Browser, BrowserContext, Page


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """配置浏览器启动参数"""
    return {
        **browser_type_launch_args,
        "headless": True,  # 无头模式，设为False可查看浏览器操作
        "slow_mo": 500,    # 每步操作延迟500ms，便于观察
    }


@pytest.fixture
def page(context: BrowserContext) -> Page:
    """创建新的页面实例"""
    page = context.new_page()
    yield page
    page.close()
