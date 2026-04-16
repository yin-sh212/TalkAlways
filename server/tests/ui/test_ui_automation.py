"""
Web端UI自动化测试 - 使用Playwright框架验证前端功能和交互
注意：此测试需要安装playwright并运行 `playwright install` 命令
运行方式: pytest tests/ui/ -v --headed（显示浏览器）或 pytest tests/ui/ -v（无头模式）
"""
import pytest
from playwright.sync_api import Page, expect


# 基础URL配置
BASE_URL = "http://localhost:8080"


class TestLoginPage:
    """登录页面测试"""
    
    def test_login_page_loads(self, page: Page):
        """测试登录页面可以正常加载"""
        page.goto(f"{BASE_URL}/login")
        
        # 验证页面标题
        expect(page).to_have_title("登录")
        
        # 验证关键元素存在
        expect(page.locator("input[placeholder*='账号']")).to_be_visible()
        expect(page.locator("input[placeholder*='密码']")).to_be_visible()
        expect(page.locator("button", has_text="登录")).to_be_visible()
    
    def test_login_with_valid_credentials(self, page: Page):
        """测试使用有效凭证登录"""
        page.goto(f"{BASE_URL}/login")
        
        # 填写登录表单
        page.fill("input[placeholder*='账号']", "13800138000")
        page.fill("input[placeholder*='密码']", "123456")
        
        # 点击登录按钮
        page.click("button", has_text="登录")
        
        # 等待跳转（可能需要调整选择器）
        page.wait_for_url("**/overview", timeout=10000)
        
        # 验证成功跳转到主页
        assert "/overview" in page.url or "/home" in page.url
    
    def test_login_with_invalid_credentials(self, page: Page):
        """测试使用无效凭证登录"""
        page.goto(f"{BASE_URL}/login")
        
        # 填写错误密码
        page.fill("input[placeholder*='账号']", "13800138000")
        page.fill("input[placeholder*='密码']", "wrongpassword")
        
        # 点击登录
        page.click("button", has_text="登录")
        
        # 应该显示错误提示（需要根据实际UI调整选择器）
        error_message = page.locator(".error-message, .el-message--error, [role='alert']")
        expect(error_message).to_be_visible(timeout=5000)


class TestOverviewPage:
    """概览页面测试"""
    
    def test_overview_page_loads(self, page: Page):
        """测试概览页面加载"""
        # 先登录
        page.goto(f"{BASE_URL}/login")
        page.fill("input[placeholder*='账号']", "13800138000")
        page.fill("input[placeholder*='密码']", "123456")
        page.click("button", has_text="登录")
        page.wait_for_url("**/overview", timeout=10000)
        
        # 验证概览页面元素
        expect(page.locator(".overview-container, #overview")).to_be_visible()
        
        # 验证KPI卡片存在
        kpi_cards = page.locator(".kpi-card, .stat-card")
        expect(kpi_cards.first).to_be_visible()
    
    def test_building_selection(self, page: Page):
        """测试建筑选择功能"""
        page.goto(f"{BASE_URL}/overview")
        
        # 等待页面加载
        page.wait_for_load_state("networkidle")
        
        # 选择建筑下拉框（需要根据实际UI调整）
        building_select = page.locator("select, .el-select, [data-testid='building-select']")
        if building_select.count() > 0:
            building_select.select_option(label="Eagle_education_Cassie")
            
            # 验证数据更新
            page.wait_for_timeout(1000)  # 等待数据加载
            
            # 验证图表或数据区域有内容
            chart_area = page.locator(".chart-container, canvas, svg")
            expect(chart_area.first).to_be_visible()
    
    def test_energy_chart_display(self, page: Page):
        """测试能耗图表显示"""
        page.goto(f"{BASE_URL}/overview")
        page.wait_for_load_state("networkidle")
        
        # 验证图表容器存在
        chart_container = page.locator(".chart, .echarts-container, canvas")
        expect(chart_container.first).to_be_visible()
        
        # 验证图表有数据（检查canvas或svg元素）
        chart_element = page.locator("canvas, svg").first
        expect(chart_element).to_be_visible()


class TestAlarmPage:
    """报警页面测试"""
    
    def test_alarm_page_loads(self, page: Page):
        """测试报警页面加载"""
        page.goto(f"{BASE_URL}/alarm")
        
        # 验证报警列表存在
        alarm_list = page.locator(".alarm-list, .alarm-table, [data-testid='alarm-list']")
        expect(alarm_list).to_be_visible()
    
    def test_alarm_filter(self, page: Page):
        """测试报警筛选功能"""
        page.goto(f"{BASE_URL}/alarm")
        
        # 查找筛选器
        filter_button = page.locator("button", has_text="筛选")
        if filter_button.count() > 0:
            filter_button.click()
            
            # 验证筛选选项出现
            filter_options = page.locator(".filter-options, .el-dropdown-menu")
            expect(filter_options).to_be_visible()


class TestAnalysisPage:
    """分析页面测试"""
    
    def test_analysis_page_loads(self, page: Page):
        """测试分析页面加载"""
        page.goto(f"{BASE_URL}/analysis")
        
        # 验证分析工具存在
        analysis_tools = page.locator(".analysis-tools, .chart-controls")
        expect(analysis_tools).to_be_visible()
    
    def test_chart_generation(self, page: Page):
        """测试图表生成功能"""
        page.goto(f"{BASE_URL}/analysis")
        
        # 选择建筑和时间范围
        building_select = page.locator("select").first
        if building_select.count() > 0:
            building_select.select_option(index=0)
            
            # 点击生成图表按钮
            generate_button = page.locator("button", has_text="生成")
            if generate_button.count() > 0:
                generate_button.click()
                
                # 等待图表加载
                page.wait_for_timeout(2000)
                
                # 验证图表出现
                chart = page.locator("canvas, svg, .chart").first
                expect(chart).to_be_visible()


class TestNavigation:
    """导航测试"""
    
    def test_navigation_menu(self, page: Page):
        """测试导航菜单功能"""
        page.goto(f"{BASE_URL}/overview")
        
        # 验证导航菜单存在
        nav_menu = page.locator(".nav-menu, .sidebar, [role='navigation']")
        expect(nav_menu).to_be_visible()
        
        # 测试各个导航项
        nav_items = [
            ("概览", "/overview"),
            ("报警", "/alarm"),
            ("分析", "/analysis"),
        ]
        
        for item_text, expected_path in nav_items:
            nav_item = page.locator(f"a:has-text('{item_text}'), .nav-item:has-text('{item_text}')")
            if nav_item.count() > 0:
                nav_item.click()
                page.wait_for_timeout(500)
                
                # 验证URL变化
                assert expected_path in page.url or page.url.endswith(expected_path)


class TestDataExport:
    """数据导出功能测试"""
    
    def test_export_functionality(self, page: Page):
        """测试数据导出功能"""
        page.goto(f"{BASE_URL}/analysis")
        
        # 查找导出按钮
        export_button = page.locator("button", has_text="导出")
        if export_button.count() > 0:
            # 监听下载事件
            with page.expect_download() as download_info:
                export_button.click()
            
            download = download_info.value
            
            # 验证文件下载
            assert download.suggested_filename
            print(f"下载文件: {download.suggested_filename}")


# Fixtures
@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """配置浏览器上下文参数"""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "locale": "zh-CN",
    }


@pytest.fixture(autouse=True)
def setup_page(page: Page):
    """自动设置页面超时和默认行为"""
    page.set_default_timeout(10000)
    page.set_default_navigation_timeout(15000)
    yield page
