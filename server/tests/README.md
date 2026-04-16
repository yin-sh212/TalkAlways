# 自动化测试指南

本文档详细说明项目的自动化测试体系、测试用例组织及执行方法。

## 📋 测试目录结构

```
server/tests/
├── __init__.py
├── conftest.py              # 全局fixtures配置
├── unit/                    # 单元测试
│   ├── test_config.py       # 配置模块测试
│   ├── test_helpers.py      # 工具函数测试
│   └── test_validation.py   # 数据验证测试
├── integration/             # 集成测试
│   ├── test_smoke.py        # 冒烟测试
│   ├── test_health_api.py   # 健康检查API测试
│   ├── test_query_api.py    # 数据查询API测试
│   ├── test_statistics_api.py # 统计分析API测试
│   ├── test_auth_api.py     # 认证API测试
│   ├── test_model_accuracy.py # 模型精度测试
│   └── test_performance.py  # 性能测试
└── ui/                      # UI自动化测试（需Playwright）
    ├── __init__.py
    ├── conftest.py          # UI测试配置
    ├── playwright.config.py # Playwright配置
    └── test_ui_automation.py # UI功能测试
```

## 🔧 环境准备

### 1. 安装测试依赖

```bash
cd server
pip install pytest pytest-asyncio pytest-cov httpx
```

### 2. 安装Playwright（UI测试可选）

```bash
pip install playwright
playwright install chromium
```

## 🚀 测试执行

### 快速开始

**一键运行所有测试：**
```bash
cd server
python run_all_tests.py
```

### 分类执行

#### 1. 单元测试

```bash
# 运行所有单元测试
python -m pytest tests/unit/ -v

# 运行特定单元测试
python -m pytest tests/unit/test_validation.py -v
python -m pytest tests/unit/test_config.py::TestConfig::test_app_name_exists -v
```

#### 2. 集成测试

```bash
# 运行所有集成测试
python -m pytest tests/integration/ -v

# 运行冒烟测试
python -m pytest tests/integration/test_smoke.py -v

# 运行API测试
python -m pytest tests/integration/test_health_api.py -v
python -m pytest tests/integration/test_query_api.py -v

# 运行模型精度测试
python -m pytest tests/integration/test_model_accuracy.py -v

# 运行性能测试
python -m pytest tests/integration/test_performance.py -v -s
```

#### 3. UI自动化测试

```bash
# 无头模式运行（推荐CI/CD）
python -m pytest tests/ui/ -v

# 显示浏览器运行过程（调试用）
python -m pytest tests/ui/ -v --headed

# 运行特定UI测试
python -m pytest tests/ui/test_ui_automation.py::TestLoginPage -v
```

### 高级选项

#### 生成覆盖率报告

```bash
# 生成HTML覆盖率报告
python -m pytest tests/ --cov=app --cov-report=html

# 查看终端覆盖率摘要
python -m pytest tests/ --cov=app --cov-report=term-missing

# 打开覆盖率报告
# macOS/Linux: open htmlcov/index.html
# Windows: start htmlcov\index.html
```

#### 并行执行测试

```bash
# 安装pytest-xdist
pip install pytest-xdist

# 使用4个进程并行执行
python -m pytest tests/ -n 4 -v
```

#### 失败重试

```bash
# 安装pytest-rerunfailures
pip install pytest-rerunfailures

# 失败用例自动重试2次
python -m pytest tests/ --reruns 2 -v
```

#### 标记测试

```bash
# 只运行标记为ui的测试
python -m pytest tests/ -m ui -v

# 跳过慢速测试
python -m pytest tests/ -m "not slow" -v
```

## 📊 测试类型说明

### 1. 冒烟测试 (test_smoke.py)

**目的：** 验证系统核心服务是否正常启动和运行

**测试内容：**
- 应用启动和健康检查
- 数据库连接与读写
- 核心API端点存在性
- 用户认证流程
- 数据查询能力
- 错误处理机制

**执行时间：** ~5秒

### 2. 单元测试 (tests/unit/)

**目的：** 验证独立模块的正确性

**测试内容：**
- 配置加载与验证
- 数据格式校验（手机号、邮箱）
- 工具函数逻辑

**特点：** 不依赖外部服务，执行速度快

### 3. 集成测试 (tests/integration/)

**目的：** 验证模块间协作和API接口

**测试内容：**
- **健康检查API：** 根路径、健康端点、CORS、错误处理
- **数据查询API：** 建筑列表、监测点、原始数据、过滤、分页
- **统计分析API：** 汇总统计、COP计算、异常检测、图表数据
- **认证API：** 登录、注册、Token验证
- **模型精度：** 异常检测算法准确性、预测模型、RAG问答质量
- **性能测试：** 响应时间、吞吐量、并发稳定性

**特点：** 需要数据库连接，模拟真实HTTP请求

### 4. UI自动化测试 (tests/ui/)

**目的：** 验证前端页面功能和用户交互

**测试内容：**
- 登录页面：加载、有效/无效凭证登录
- 概览页面：元素可见性、建筑选择、图表显示
- 报警页面：列表加载、筛选功能
- 分析页面：图表生成、数据导出
- 导航菜单：页面跳转

**特点：** 需要运行前端开发服务器，使用Playwright驱动浏览器

## 🎯 测试覆盖目标

| 测试类型 | 覆盖率目标 | 当前状态 |
|---------|-----------|---------|
| 单元测试 | 80%+ | ✅ 已实现 |
| 集成测试 | 70%+ | ✅ 已实现 |
| UI测试 | 核心流程100% | ✅ 已实现 |
| 性能测试 | 关键接口100% | ✅ 已实现 |

## 📈 测试结果解读

### 通过标准

- **单元测试：** 100% 通过
- **集成测试：** ≥95% 通过
- **UI测试：** 核心流程100% 通过
- **性能指标：**
  - 健康检查 < 200ms
  - 单建筑月度能耗查询 < 200ms
  - COP计算 < 500ms
  - RAG问答 < 3000ms
  - 并发成功率 ≥ 95%

### 常见问题排查

#### 1. 数据库连接失败

```bash
# 检查.env配置
cat .env | grep DB_

# 测试数据库连通性
python -c "from app.database.db import Database; import asyncio; asyncio.run(Database.fetch_one('SELECT 1'))"
```

#### 2. UI测试失败

```bash
# 确认前端服务运行
curl http://localhost:8080

# 更新Playwright浏览器
playwright install --force

# 调试模式运行（显示浏览器）
python -m pytest tests/ui/ -v --headed --slowmo=1000
```

#### 3. 性能测试不达标

```bash
# 单独运行性能测试查看详细日志
python -m pytest tests/integration/test_performance.py -v -s

# 检查数据库索引
python scripts/add_indexes.py

# 清理缓存重启服务
```

## 🔍 编写新测试

### 单元测试模板

```python
"""模块功能单元测试"""
import pytest
from app.your_module import your_function

class TestYourFunction:
    def test_normal_case(self):
        """测试正常情况"""
        result = your_function(valid_input)
        assert result == expected_output
    
    def test_edge_case(self):
        """测试边界情况"""
        result = your_function(edge_input)
        assert result == expected_edge_output
    
    def test_error_handling(self):
        """测试错误处理"""
        with pytest.raises(ValueError):
            your_function(invalid_input)
```

### 集成测试模板

```python
"""API集成测试"""
import pytest
from httpx import AsyncClient

class TestYourEndpoint:
    @pytest.mark.asyncio
    async def test_endpoint_success(self, async_client: AsyncClient):
        """测试接口成功场景"""
        response = await async_client.get("/api/your-endpoint")
        assert response.status_code == 200
        data = response.json()
        assert "expected_field" in data
    
    @pytest.mark.asyncio
    async def test_endpoint_with_params(self, async_client: AsyncClient):
        """测试带参数的接口"""
        params = {"param1": "value1"}
        response = await async_client.get("/api/your-endpoint", params=params)
        assert response.status_code == 200
```

### UI测试模板

```python
"""UI功能测试"""
import pytest
from playwright.sync_api import Page, expect

class TestYourPage:
    def test_page_loads(self, page: Page):
        """测试页面加载"""
        page.goto("http://localhost:8080/your-page")
        expect(page).to_have_title("预期标题")
        expect(page.locator(".key-element")).to_be_visible()
    
    def test_user_interaction(self, page: Page):
        """测试用户交互"""
        page.goto("http://localhost:8080/your-page")
        page.click("button", has_text="操作")
        expect(page.locator(".result")).to_be_visible()
```

## 📝 最佳实践

1. **测试命名规范：** 使用描述性的测试名称，如 `test_login_with_valid_credentials`
2. **AAA原则：** Arrange（准备）- Act（执行）- Assert（断言）
3. **独立性：** 每个测试用例应独立运行，不依赖其他测试的状态
4. **可重复性：** 测试结果应一致，避免随机性和时序依赖
5. **快速反馈：** 单元测试应在毫秒级完成，集成测试在秒级完成
6. **清晰断言：** 使用明确的断言消息，便于问题定位
7. **测试数据隔离：** 使用fixtures提供测试数据，避免硬编码

## 🛠️ CI/CD集成

### GitHub Actions示例

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          cd server
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      
      - name: Run tests
        run: |
          cd server
          python -m pytest tests/ --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## 📞 技术支持

如遇测试相关问题，请：
1. 查看测试输出日志
2. 检查 `.env` 配置文件
3. 确认数据库服务正常运行
4. 参考本文档的"常见问题排查"章节
