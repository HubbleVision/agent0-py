#!/usr/bin/env python3
"""
端到端 BNB Greenfield E2E 测试

本脚本简化了 E2E 测试的运行，不依赖 pytest，
直接运行测试来验证 Greenfield 存储的完整工作流程。

使用方法：
python run_greenfield_e2e.py
或：
python run_greenfield_e2e.py all

运行选项：
python run_greenfield_e2e.py small   # 小文本测试
python run_greenfield_e2e.py json    # JSON 数据测试
python run_greenfield_e2e.py binary  # 二进制数据测试
python run_greenfield_e2e.py large   # 大数据性能测试
python run_greenfield_e2e.py all     # 运行所有测试
"""

import asyncio
import json
import os
import sys
import time
import hashlib
import logging
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from agent0_sdk.core.greenfield_storage import GreenfieldReputationStorage
    from agent0_sdk.core.storage_interfaces import ReputationStorage
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保在 agent0-py 目录中运行此脚本，或者已正确安装依赖。")
    sys.exit(1)

# E2E 测试数据
TEST_DATA_EXAMPLES = {
    "small_text": "你好，Greenfield！这是一个 E2E 测试消息。".encode('utf-8'),
    "json_data": json.dumps({
        "agent_id": "test-agent-123",
        "reputation": {
            "score": 95,
            "reviews": [
                {"rating": 5, "comment": "出色的工作"},
                {"rating": 4, "comment": "良好表现"}
            ],
            "created_at": "2024-11-28T14:30:00Z"
        }
    }, ensure_ascii=False).encode('utf-8'),
    "binary_data": bytes([i % 256 for i in range(256)]),  # 包含所有可能的字节值
    "large_data": b"X" * 1024,  # 1KB
    "very_large_data": b"Performance test data. " * 10000,  # ~320KB
}


def check_environment() -> Dict[str, Any]:
    """检查环境配置。"""
    print("🔍 检查环境配置...")

    # 必需字段
    required_fields = [
        "GREENFIELD_BUCKET",
        "GREENFIELD_PRIVATE_KEY",
        "GREENFIELD_SP_HOST"
    ]

    # 可选字段
    optional_fields = [
        "GREENFIELD_TXN_HASH",
        "GREENFIELD_CONTENT_TYPE",
        "GREENFIELD_TIMEOUT"
    ]

    config = {}
    missing_fields = []

    for field in required_fields:
        value = os.getenv(field)
        if value:
            config[field] = value
        else:
            missing_fields.append(field)

    for field in optional_fields:
        value = os.getenv(field)
        if value:
            config[field] = value

    if missing_fields:
        print("❌ 缺少必需的环境变量：")
        for field in missing_fields:
            print(f"   - {field}")
        print(f"\n📖 请参考 .env 文件配置环境变量。")
        return None

    print(f"✅ 环境配置检查通过")
    print(f"   - Bucket: {config['GREENFIELD_BUCKET']}")
    print(f"   - SP Host: {config['GREENFIELD_SP_HOST']}")
    print(f"   - Has Txn Hash: {'GREENFIELD_TXN_HASH' in config}")
    return config


def create_greenfield_storage(config: Dict[str, Any]) -> GreenfieldReputationStorage:
    """创建 Greenfield 存储实例。"""
    try:
        storage = GreenfieldReputationStorage(
            sp_host=config["GREENFIELD_SP_HOST"],
            bucket=config["GREENFIELD_BUCKET"],
            private_key=config["GREENFIELD_PRIVATE_KEY"],
            txn_hash=config.get("GREENFIELD_TXN_HASH"),
            content_type=config.get("GREENFIELD_CONTENT_TYPE", "application/octet-stream"),
            timeout=int(config.get("GREENFIELD_TIMEOUT", 30))
        )
        print(f"✅ Greenfield 存储创建成功")
        return storage
    except Exception as e:
        print(f"❌ 创建 Greenfield 存储失败: {e}")
        raise


async def test_upload_download(storage: GreenfieldReputationStorage, test_name: str, data: bytes, key: Optional[str] = None) -> bool:
    """测试上传和下载的完整流程。"""
    print(f"\n🚀 开始测试: {test_name}")
    print(f"   数据大小: {len(data)} 字节")

    try:
        # 上传数据
        start_time = time.time()
        object_key = storage.put(key, data)
        upload_time = time.time() - start_time

        print(f"✅ 上传成功:")
        print(f"   对象键: {object_key}")
        print(f"   上传时间: {upload_time:.2f} 秒")
        print(f"   上传速度: {len(data) / upload_time:.2f} 字节/秒")

        # 下载数据
        start_time = time.time()
        downloaded_data = storage.get(object_key)
        download_time = time.time() - start_time

        print(f"✅ 下载成功:")
        print(f"   下载大小: {len(downloaded_data)} 字节")
        print(f"   下载时间: {download_time:.2f} 秒")
        print(f"   下载速度: {len(downloaded_data) / download_time:.2f} 字节/秒")

        # 验证数据完整性
        if downloaded_data == data:
            print(f"✅ 数据完整性验证通过")

            # 计算哈希值
            original_hash = hashlib.sha256(data).hexdigest()
            downloaded_hash = hashlib.sha256(downloaded_data).hexdigest()
            print(f"   原始数据 SHA256: {original_hash[:16]}...")
            print(f"   下载数据 SHA256: {downloaded_hash[:16]}...")

            return True
        else:
            print(f"❌ 数据完整性验证失败")
            print(f"   原始数据长度: {len(data)}")
            print(f"   下载数据长度: {len(downloaded_data)}")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


async def test_error_handling(storage: GreenfieldReputationStorage) -> bool:
    """测试错误处理。"""
    print(f"\n🧪 开始错误处理测试")

    try:
        # 测试获取不存在的对象
        print("   测试获取不存在的对象...")
        try:
            storage.get("non-existent-object-key-12345")
            print("❌ 应该抛出异常但没有")
            return False
        except RuntimeError as e:
            print(f"✅ 正确抛出异常: {type(e).__name__}")

        # 测试上传时缺少 txn_hash
        print("   测试上传时缺少 txn_hash...")
        # 创建一个没有默认 txn_hash 的存储实例
        try:
            storage_no_txn = GreenfieldReputationStorage(
                sp_host=os.getenv("GREENFIELD_SP_HOST"),
                bucket=os.getenv("GREENFIELD_BUCKET"),
                private_key=os.getenv("GREENFIELD_PRIVATE_KEY"),
                txn_hash=None  # 没有默认 txn_hash
            )
            storage_no_txn.put("test-key", b"test data")
            print("❌ 应该抛出异常但没有")
            return False
        except ValueError as e:
            print(f"✅ 正确抛出异常: {type(e).__name__}")
            print(f"   错误信息: {str(e)[:100]}...")

        print(f"✅ 错误处理测试通过")
        return True

    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")
        return False


async def test_performance(storage: GreenfieldReputationStorage) -> bool:
    """测试性能。"""
    print(f"\n⚡ 开始性能测试")

    try:
        # 测试不同大小的数据
        test_sizes = [
            (b"Small test", "小数据"),
            (b"X" * 1024, "1KB 数据"),
            (b"Y" * 10240, "10KB 数据"),
            (b"Z" * 102400, "100KB 数据"),
        ]

        performance_results = []

        for data, description in test_sizes:
            print(f"   测试 {description} ({len(data)} 字节)...")

            # 上传性能测试
            start_time = time.time()
            object_key = storage.put(None, data)
            upload_time = time.time() - start_time

            # 下载性能测试
            start_time = time.time()
            downloaded_data = storage.get(object_key)
            download_time = time.time() - start_time

            # 计算速度
            upload_speed = len(data) / upload_time
            download_speed = len(downloaded_data) / download_time

            performance_results.append({
                "description": description,
                "size": len(data),
                "upload_time": upload_time,
                "download_time": download_time,
                "upload_speed": upload_speed,
                "download_speed": download_speed
            })

            print(f"     上传: {upload_time:.2f}s ({upload_speed:.2f} B/s)")
            print(f"     下载: {download_time:.2f}s ({download_speed:.2f} B/s)")

        # 显示性能总结
        print(f"\n📊 性能总结:")
        print(f"{'描述':<15} {'大小':<10} {'上传速度':<15} {'下载速度':<15}")
        print("-" * 60)
        for result in performance_results:
            print(f"{result['description']:<15} {result['size']:<10} "
                  f"{result['upload_speed']:<15.2f} {result['download_speed']:<15.2f}")

        print(f"✅ 性能测试完成")
        return True

    except Exception as e:
        print(f"❌ 性能测试失败: {e}")
        return False


async def run_all_tests(storage: GreenfieldReputationStorage) -> Dict[str, bool]:
    """运行所有测试。"""
    print(f"\n🧪 开始运行完整的 E2E 测试套件")

    results = {}

    # 基础数据测试
    for test_name, data in TEST_DATA_EXAMPLES.items():
        if test_name == "very_large_data":
            continue  # 单独测试大数据
        results[test_name] = await test_upload_download(storage, test_name, data)

    # 自动生成键测试
    print(f"\n🔑 测试自动生成对象键...")
    results["auto_key"] = await test_upload_download(storage, "自动键生成", b"Auto-generated key test", None)

    # 指定键测试
    print(f"\n🏷️ 测试指定对象键...")
    results["manual_key"] = await test_upload_download(storage, "手动键", b"Manual key test", "test-manual-key-123")

    # 错误处理测试
    results["error_handling"] = await test_error_handling(storage)

    # 性能测试
    results["performance"] = await test_performance(storage)

    # 大数据测试（如果环境允许）
    print(f"\n📦 测试大数据 (~320KB)...")
    results["very_large_data"] = await test_upload_download(storage, "大数据测试", TEST_DATA_EXAMPLES["very_large_data"])

    return results


def print_summary(results: Dict[str, bool]) -> None:
    """打印测试结果总结。"""
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
        print(f"🎉 所有测试通过！Greenfield 存储工作正常。")
    else:
        print(f"⚠️ 有 {total - passed} 个测试失败，请检查配置和网络连接。")


async def main():
    """主函数。"""
    print("🌟 BNB Greenfield E2E 测试")
    print("=" * 50)

    # 加载环境变量
    load_dotenv()

    # 解析命令行参数
    test_type = sys.argv[1] if len(sys.argv) > 1 else "all"

    # 检查环境配置
    config = check_environment()
    if not config:
        sys.exit(1)

    # 创建存储实例
    try:
        storage = create_greenfield_storage(config)
    except Exception:
        sys.exit(1)

    # 运行测试
    try:
        if test_type == "all":
            results = await run_all_tests(storage)
        elif test_type == "small":
            results = {"small_text": await test_upload_download(storage, "小文本测试", TEST_DATA_EXAMPLES["small_text"])}
        elif test_type == "json":
            results = {"json_data": await test_upload_download(storage, "JSON数据测试", TEST_DATA_EXAMPLES["json_data"])}
        elif test_type == "binary":
            results = {"binary_data": await test_upload_download(storage, "二进制数据测试", TEST_DATA_EXAMPLES["binary_data"])}
        elif test_type == "large":
            results = {"large_data": await test_upload_download(storage, "大数据测试", TEST_DATA_EXAMPLES["large_data"])}
        else:
            print(f"❌ 未知的测试类型: {test_type}")
            print("可用选项: small, json, binary, large, all")
            sys.exit(1)

        # 打印总结
        print_summary(results)

        # 返回适当的退出码
        sys.exit(0 if all(results.values()) else 1)

    except KeyboardInterrupt:
        print(f"\n⚠️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试运行失败: {e}")
        logger.exception("Test execution failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())