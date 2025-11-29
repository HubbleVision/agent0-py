#!/usr/bin/env python3
"""
基础的 Greenfield 存储配置验证测试

这个脚本用于验证 Greenfield 存储配置是否正确，
不需要真实的 Transaction Hash，只测试基本的初始化和错误处理。
"""

import os
import sys
from dotenv import load_dotenv

# Add project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from agent0_sdk.core.greenfield_storage import GreenfieldReputationStorage
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保在 agent0-py 目录中运行此脚本，或者已正确安装依赖。")
    sys.exit(1)


def test_basic_initialization():
    """测试基本的初始化功能。"""
    print("🧪 测试基本初始化...")

    try:
        # 测试缺少必需参数
        try:
            GreenfieldReputationStorage(
                sp_host="",  # 空字符串应该失败
                bucket="test",
                private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
            )
            print("❌ 应该失败但成功了")
            return False
        except ValueError as e:
            print(f"✅ 正确捕获 sp_host 错误: {e}")

        try:
            GreenfieldReputationStorage(
                sp_host="test.com",
                bucket="",  # 空字符串应该失败
                private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
            )
            print("❌ 应该失败但成功了")
            return False
        except ValueError as e:
            print(f"✅ 正确捕获 bucket 错误: {e}")

        try:
            GreenfieldReputationStorage(
                sp_host="test.com",
                bucket="test",
                private_key=""  # 空字符串应该失败
            )
            print("❌ 应该失败但成功了")
            return False
        except ValueError as e:
            print(f"✅ 正确捕获 private_key 错误: {e}")

        # 测试正确的初始化（但没有 txn_hash）
        storage = GreenfieldReputationStorage(
            sp_host="gnfd-testnet-sp1.bnbchain.org",
            bucket="test-bucket",
            private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        print(f"✅ 基本初始化成功")
        print(f"   Wallet: {storage.account.address}")
        print(f"   Bucket: {storage.bucket}")
        print(f"   SP Host: {storage.sp_host}")
        print(f"   Has Default Txn Hash: {bool(storage.default_txn_hash)}")

        return True

    except Exception as e:
        print(f"❌ 基本初始化测试失败: {e}")
        return False


def test_environment_variables():
    """测试环境变量配置。"""
    print("\n🔧 测试环境变量配置...")

    # 加载环境变量
    load_dotenv()

    required_vars = ["GREENFIELD_SP_HOST", "GREENFIELD_BUCKET", "GREENFIELD_PRIVATE_KEY"]
    optional_vars = ["GREENFIELD_TXN_HASH", "GREENFIELD_CONTENT_TYPE", "GREENFIELD_TIMEOUT"]

    config_status = {}

    # 检查必需变量
    for var in required_vars:
        value = os.getenv(var)
        if value:
            config_status[var] = "✅ 已设置"
            if "PRIVATE_KEY" in var:
                config_status[var] += f" (0x{value[-10:]})"  # 只显示最后几位
            else:
                config_status[var] += f" ({value})"
        else:
            config_status[var] = "❌ 未设置"

    # 检查可选变量
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            config_status[var] = "✅ 已设置"
            if "PRIVATE_KEY" not in var:
                config_status[var] += f" ({value})"
            else:
                config_status[var] += f" (0x{value[-10:]})"
        else:
            config_status[var] = "⚪ 未设置 (可选)"

    # 打印状态
    for var, status in config_status.items():
        print(f"   {var}: {status}")

    # 检查是否所有必需变量都已设置
    missing_required = [var for var in required_vars if not os.getenv(var)]
    if missing_required:
        print(f"\n❌ 缺少必需的环境变量: {', '.join(missing_required)}")
        return False

    print(f"\n✅ 所有必需的环境变量已设置")
    return True


def test_with_environment_config():
    """使用环境变量配置进行测试。"""
    print("\n⚙️ 测试使用环境变量配置...")

    try:
        # 从环境变量加载配置
        config = {
            "sp_host": os.getenv("GREENFIELD_SP_HOST"),
            "bucket": os.getenv("GREENFIELD_BUCKET"),
            "private_key": os.getenv("GREENFIELD_PRIVATE_KEY"),
            "txn_hash": os.getenv("GREENFIELD_TXN_HASH"),
            "content_type": os.getenv("GREENFIELD_CONTENT_TYPE", "application/octet-stream"),
            "timeout": int(os.getenv("GREENFIELD_TIMEOUT", 30))
        }

        # 检查必需配置
        if not all([config["sp_host"], config["bucket"], config["private_key"]]):
            print("❌ 缺少必需的配置")
            return False

        # 创建存储实例
        storage = GreenfieldReputationStorage(**config)

        print(f"✅ 使用环境变量创建存储成功")
        print(f"   SP Host: {storage.sp_host}")
        print(f"   Bucket: {storage.bucket}")
        print(f"   Wallet: {storage.account.address}")
        print(f"   Content Type: {storage.content_type}")
        print(f"   Timeout: {storage.timeout}")
        print(f"   Has Default Txn Hash: {bool(storage.default_txn_hash)}")

        # 测试对象键生成
        test_key = storage._gen_key()
        print(f"✅ 对象键生成成功: {test_key}")

        # 测试签名构建（不实际发送请求）
        test_headers = {
            "Content-Type": "application/octet-stream",
            "Content-Length": "100",
            "X-Gnfd-Txn-Hash": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "X-Gnfd-Expiry-Timestamp": "2024-11-29T00:00:00Z"
        }

        auth_header = storage._build_authorization(
            method="PUT",
            path="/test-object",
            headers=test_headers,
            body=b"test data"
        )

        print(f"✅ 签名构建成功: {auth_header[:50]}...")

        return True

    except Exception as e:
        print(f"❌ 环境变量配置测试失败: {e}")
        return False


def test_error_conditions():
    """测试错误条件。"""
    print("\n🚨 测试错误条件...")

    try:
        # 创建一个没有默认 txn_hash 的存储实例
        storage = GreenfieldReputationStorage(
            sp_host="gnfd-testnet-sp1.bnbchain.org",
            bucket="test-bucket",
            private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )

        # 测试没有 txn_hash 的 put 操作
        try:
            storage.put("test-key", b"test data")
            print("❌ 应该失败但成功了")
            return False
        except ValueError as e:
            print(f"✅ 正确捕获 txn_hash 错误: {str(e)[:100]}...")

        # 测试获取不存在的对象（这会失败，但我们想测试错误处理）
        try:
            storage.get("non-existent-object")
            print("⚠️ 获取不存在的对象没有抛出异常（可能是公开对象）")
        except RuntimeError as e:
            print(f"✅ 正确捕获获取错误: {type(e).__name__}")

        return True

    except Exception as e:
        print(f"❌ 错误条件测试失败: {e}")
        return False


def main():
    """主函数。"""
    print("🌟 Greenfield 基础配置验证测试")
    print("=" * 50)

    results = {}

    # 运行测试
    results["basic_init"] = test_basic_initialization()
    results["env_vars"] = test_environment_variables()
    results["env_config"] = test_with_environment_config()
    results["error_handling"] = test_error_conditions()

    # 打印总结
    print(f"\n📋 测试结果总结")
    print("=" * 50)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<25} {status}")

    print("-" * 50)
    print(f"总计: {passed}/{total} 测试通过")

    if passed == total:
        print(f"\n🎉 所有基础测试通过！")
        print(f"💡 下一步：")
        print(f"   1. 获取真实的 Transaction Hash（参考 GREENFIELD_E2E_运行指南.md）")
        print(f"   2. 更新 .env 文件中的 GREENFIELD_TXN_HASH")
        print(f"   3. 运行完整的 E2E 测试：python tests/run_greenfield_e2e.py all")
    else:
        print(f"\n⚠️ 有 {total - passed} 个测试失败，请检查配置。")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())