"""
测试运行脚本
使用方法:
    python run_tests.py              # 运行所有测试
    python run_tests.py unit         # 只运行单元测试
    python run_tests.py integration  # 只运行集成测试
    python run_tests.py --cov        # 运行测试并生成覆盖率报告
"""
import subprocess
import sys
import os


def run_tests(test_type="all", with_coverage=False):
    """运行测试"""
    
    # 切换到server目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # 构建pytest命令
    cmd = [sys.executable, "-m", "pytest"]
    
    # 添加测试路径
    if test_type == "unit":
        cmd.append("tests/unit/")
    elif test_type == "integration":
        cmd.append("tests/integration/")
    else:
        cmd.append("tests/")
    
    # 添加详细输出选项
    cmd.extend(["-v", "--tb=short"])
    
    # 添加覆盖率选项
    if with_coverage:
        cmd.extend([
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov"
        ])
    
    print(f"\n{'='*60}")
    print(f"运行{test_type.upper()}测试")
    print(f"{'='*60}\n")
    print(f"执行命令: {' '.join(cmd)}\n")
    
    # 运行测试
    result = subprocess.run(cmd)
    
    # 返回退出码
    return result.returncode


if __name__ == "__main__":
    # 解析命令行参数
    test_type = "all"
    with_coverage = False
    
    for arg in sys.argv[1:]:
        if arg in ["unit", "integration"]:
            test_type = arg
        elif arg == "--cov":
            with_coverage = True
    
    # 运行测试
    exit_code = run_tests(test_type, with_coverage)
    
    # 输出结果
    print(f"\n{'='*60}")
    if exit_code == 0:
        print("✅ 所有测试通过!")
    else:
        print(f"❌ 测试失败，退出码: {exit_code}")
    print(f"{'='*60}\n")
    
    sys.exit(exit_code)
