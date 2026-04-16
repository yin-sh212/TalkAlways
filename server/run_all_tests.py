#!/usr/bin/env python
"""
测试运行脚本 - 一键执行所有测试并生成报告
"""
import subprocess
import sys
import os


def run_command(cmd, description):
    """运行命令并输出结果"""
    print(f"\n{'='*60}")
    print(f"执行: {description}")
    print(f"命令: {' '.join(cmd)}")
    print('='*60)
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode != 0:
        print(f"❌ {description} 失败")
        return False
    else:
        print(f"✅ {description} 成功")
        return True


def main():
    """主函数"""
    # 切换到server目录
    server_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(server_dir)
    
    print("🚀 开始执行自动化测试套件")
    print("="*60)
    
    # 1. 运行单元测试
    unit_test_passed = run_command(
        [sys.executable, "-m", "pytest", "tests/unit/", "-v", "--tb=short"],
        "单元测试"
    )
    
    # 2. 运行集成测试（不含UI测试）
    integration_test_passed = run_command(
        [sys.executable, "-m", "pytest", 
         "tests/integration/", "-v", "--tb=short", "-x"],
        "集成测试"
    )
    
    # 3. 生成覆盖率报告
    coverage_passed = run_command(
        [sys.executable, "-m", "pytest", 
         "tests/", "--cov=app", "--cov-report=html", "--cov-report=term-missing"],
        "覆盖率测试"
    )
    
    # 4. 输出总结
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)
    print(f"单元测试:     {'✅ 通过' if unit_test_passed else '❌ 失败'}")
    print(f"集成测试:     {'✅ 通过' if integration_test_passed else '❌ 失败'}")
    print(f"覆盖率报告:   {'✅ 生成' if coverage_passed else '❌ 失败'}")
    
    if coverage_passed:
        print(f"\n📈 覆盖率报告已生成至: {os.path.join(server_dir, 'htmlcov', 'index.html')}")
        print("   在浏览器中打开该文件查看详细报告")
    
    all_passed = unit_test_passed and integration_test_passed
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️  部分测试失败，请检查上述输出")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
