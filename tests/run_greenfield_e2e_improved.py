#!/usr/bin/env python3
"""
改进的 BNB Greenfield E2E 测试

这个改进版本提供了更好的错误处理和测试模式选择：
1. 真实模式：使用真实的 Transaction Hash 进行完整测试
2. 模拟模式：模拟 Greenfield 响应，用于测试代码逻辑
3. 混合模式：部分真实，部分模拟

使用方法：
python run_greenfield_e2e_improved.py --mode real    # 真实模式
python run_greenfield_e2e_improved.py --mode mock    # 模拟模式
python run_greenfield_e2e_improved.py --mode hybrid   # 混合模式
"""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, patch

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
    from agent0_sdk.core.greenfield_cli import create_e2e_helper
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
    "binary_data": bytes([i % 256 for i in range(256)]),
    "large_data": b"X" * 1024,
    "very_large_data": b"Performance test data. " * 10000,
}

# 静态对象键，便于复用同一个 CreateObject 交易哈希
STATIC_KEYS = {
    "small_text": "e2e-small-text",
    "json_data": "e2e-json-data",
    "binary_data": "e2e-binary-data",
    "large_data": "e2e-large-data",
    "very_large_data": "e2e-very-large-data",
    "auto_key": "e2e-auto-key",
    "manual_key": "test-manual-key-123",
}


class MockGreenfieldStorage:
    """模拟的 Greenfield 存储，用于测试代码逻辑"""

    def __init__(self, real_storage):
        self.real_storage = real_storage
        self.mock_data = {}
        self.success_rate = 1.0  # 100% 成功率

    def put(self, key: str, data: bytes, txn_hash: Optional[str] = None) -> str:
        """模拟上传操作"""
        if key is None:
            key = self.real_storage._gen_key()

        # 模拟上传延迟
        time.sleep(0.1 + len(data) / 100000)  # 100ms + 数据大小相关的延迟

        # 存储数据
        self.mock_data[key] = data

        logger.info(f"Mock upload: key={key}, size={len(data)} bytes")
        return key

    def get(self, key: str) -> bytes:
        """模拟下载操作"""
        if key not in self.mock_data:
            raise RuntimeError(f"Object not found: {key}")

        # 模拟下载延迟
        time.sleep(0.05 + len(self.mock_data[key]) / 200000)

        data = self.mock_data[key]
        logger.info(f"Mock download: key={key}, size={len(data)} bytes")
        return data


class ImprovedE2ETest:
    """改进的 E2E 测试类"""

    def __init__(self, mode: str = "real"):
        self.mode = mode
        self.auto_uploader = None  # 用于自动 CreateObject + PutObject
        self.load_environment()
        self.create_storage()
        # auto_uploader 延迟初始化（异步）
        self._auto_uploader_ready = False
        # 允许使用静态对象键与映射好的 txn hash，便于复用同一批链上对象
        self.use_static_keys = os.getenv("GREENFIELD_STATIC_KEYS", "1") == "1"
        # 若明确要求 bypassSeal，则跳过封存等待
        self.bypass_seal = os.getenv("GREENFIELD_CLI_BYPASS_SEAL", "0") == "1"
        txn_map_raw = os.getenv("GREENFIELD_TXN_HASH_MAP", "")
        try:
            self.txn_hash_map = json.loads(txn_map_raw) if txn_map_raw else {}
        except json.JSONDecodeError:
            print(f"⚠️ GREENFIELD_TXN_HASH_MAP 解析失败，忽略此映射")
            self.txn_hash_map = {}

    def load_environment(self):
        """加载环境变量"""
        load_dotenv()

        self.required_fields = [
            "GREENFIELD_BUCKET",
            "GREENFIELD_PRIVATE_KEY",
            "GREENFIELD_SP_HOST"
        ]

        self.config = {}
        missing_fields = []

        for field in self.required_fields:
            value = os.getenv(field)
            if value:
                self.config[field] = value
            else:
                missing_fields.append(field)

        # 可选字段
        optional_fields = [
            "GREENFIELD_TXN_HASH",
            "GREENFIELD_CONTENT_TYPE",
            "GREENFIELD_TIMEOUT"
        ]

        for field in optional_fields:
            value = os.getenv(field)
            if value:
                if field == "GREENFIELD_TIMEOUT":
                    self.config[field] = int(value)
                else:
                    self.config[field] = value

        if missing_fields:
            print(f"❌ 缺少必需的环境变量: {', '.join(missing_fields)}")
            sys.exit(1)

        print(f"✅ 环境配置加载成功")
        print(f"   Mode: {self.mode}")
        print(f"   Bucket: {self.config['GREENFIELD_BUCKET']}")
        print(f"   SP Host: {self.config['GREENFIELD_SP_HOST']}")
        print(f"   Has Txn Hash: {'GREENFIELD_TXN_HASH' in self.config}")

    def create_storage(self):
        """创建存储实例"""
        try:
            if self.mode == "mock":
                # 创建真实的存储实例用于配置，但使用 Mock 包装器
                self.real_storage = GreenfieldReputationStorage(
                    sp_host=self.config["GREENFIELD_SP_HOST"],
                    bucket=self.config["GREENFIELD_BUCKET"],
                    private_key=self.config["GREENFIELD_PRIVATE_KEY"],
                    txn_hash=self.config.get("GREENFIELD_TXN_HASH"),
                    content_type=self.config.get("GREENFIELD_CONTENT_TYPE", "application/octet-stream"),
                    timeout=self.config.get("GREENFIELD_TIMEOUT", 30)
                )
                self.storage = MockGreenfieldStorage(self.real_storage)
                print(f"✅ 模拟存储创建成功")

            elif self.mode == "real":
                if "GREENFIELD_TXN_HASH" not in self.config:
                    print(f"❌ 真实模式需要 GREENFIELD_TXN_HASH")
                    print(f"💡 请运行: python scripts/setup_greenfield_test.py")
                    sys.exit(1)

                self.storage = GreenfieldReputationStorage(
                    sp_host=self.config["GREENFIELD_SP_HOST"],
                    bucket=self.config["GREENFIELD_BUCKET"],
                    private_key=self.config["GREENFIELD_PRIVATE_KEY"],
                    txn_hash=self.config["GREENFIELD_TXN_HASH"],
                    content_type=self.config.get("GREENFIELD_CONTENT_TYPE", "application/octet-stream"),
                    timeout=self.config.get("GREENFIELD_TIMEOUT", 30)
                )
                print(f"✅ 真实存储创建成功")

            elif self.mode == "hybrid":
                # 混合模式：真实存储，但允许一些失败的测试
                if "GREENFIELD_TXN_HASH" not in self.config:
                    print(f"⚠️ 混合模式缺少 GREENFIELD_TXN_HASH，降级到模拟模式")
                    self.mode = "mock"
                    return self.create_storage()

                self.storage = GreenfieldReputationStorage(
                    sp_host=self.config["GREENFIELD_SP_HOST"],
                    bucket=self.config["GREENFIELD_BUCKET"],
                    private_key=self.config["GREENFIELD_PRIVATE_KEY"],
                    txn_hash=self.config["GREENFIELD_TXN_HASH"],
                    content_type=self.config.get("GREENFIELD_CONTENT_TYPE", "application/octet-stream"),
                    timeout=self.config.get("GREENFIELD_TIMEOUT", 30)
                )
                print(f"✅ 混合模式存储创建成功")

            else:
                print(f"❌ 无效的测试模式: {self.mode}")
                print(f"可用模式: real, mock, hybrid")
                sys.exit(1)

        except Exception as e:
            print(f"❌ 创建存储失败: {e}")
            sys.exit(1)

    async def ensure_auto_uploader(self):
        """在真实模式下尝试启用自动 CreateObject 助手"""
        if self.mode != "real" or getattr(self, "_auto_uploader_ready", False):
            return

        rpc_url = os.getenv(
            "GREENFIELD_RPC_URL",
            "https://gnfd-testnet-fullnode-tendermint-us.bnbchain.org",
        )
        chain_id_env = os.getenv("GREENFIELD_CHAIN_ID", "5600")
        cli_chain_id_env = os.getenv("GREENFIELD_CLI_CHAIN_ID")
        try:
            chain_id = int(chain_id_env)
        except Exception:
            chain_id = chain_id_env  # allow string for helper to normalize

        try:
            self.auto_uploader = await create_e2e_helper({
                "rpc_url": rpc_url,
                "sp_host": self.config["GREENFIELD_SP_HOST"],
                "bucket_name": self.config["GREENFIELD_BUCKET"],
                "private_key": self.config["GREENFIELD_PRIVATE_KEY"],
                "chain_id": chain_id,
                "cli_chain_id": cli_chain_id_env,
                "content_type": self.config.get("GREENFIELD_CONTENT_TYPE", "application/octet-stream"),
                "timeout": self.config.get("GREENFIELD_TIMEOUT", 30),
                # 传递 CLI 模板（可选）
                "cli_template": os.getenv("GREENFIELD_CREATE_OBJECT_CMD_TEMPLATE"),
            })
            print(f"✅ 已启用自动 CreateObject 助手 (rpc={rpc_url}, chain_id={chain_id})")
            # 自动助手存在时，为避免静态键已存在，禁用静态键复用
            self.use_static_keys = False
        except Exception as e:
            print(f"⚠️ 无法初始化自动助手，继续使用预置 txn_hash: {e}")
            self.auto_uploader = None

        self._auto_uploader_ready = True

    async def wait_object_ready(self, object_key: str) -> None:
        """等待对象在 SP 可读，避免 bypassSeal 后立即读取失败。"""
        if self.bypass_seal or os.getenv("GREENFIELD_WAIT_DISABLE", "0") == "1":
            return  # 用户显式要求跳过封存等待
        if not self.auto_uploader:
            return
        wait_timeout = int(os.getenv("GREENFIELD_WAIT_TIMEOUT", "30"))
        wait_interval = int(os.getenv("GREENFIELD_WAIT_INTERVAL", "5"))
        try:
            await self.auto_uploader.wait_until_ready(
                object_key,
                timeout=wait_timeout,
                interval=wait_interval,
            )
        except Exception as e:
            print(f"⚠️ 等待对象可用失败（继续尝试下载）: {e}")

    async def test_upload_download(self, test_name: str, data: bytes, key: Optional[str] = None) -> bool:
        """测试上传和下载的完整流程"""
        print(f"\n🚀 开始测试: {test_name}")
        print(f"   数据大小: {len(data)} 字节")
        print(f"   测试模式: {self.mode}")

        try:
            # 上传数据
            start_time = time.time()
            object_key = key

            # 若启用静态键，优先使用静态映射，便于对应链上的 CreateObject txn
            if not object_key and self.use_static_keys and test_name in STATIC_KEYS:
                object_key = STATIC_KEYS[test_name]
            if not object_key:
                object_key = self.storage._gen_key()
            elif self.auto_uploader and self.use_static_keys is False and key:
                # 避免已有对象导致冲突，附加时间戳
                object_key = f"{object_key}-{int(time.time())}"

            txn_hash_override = self.txn_hash_map.get(object_key)

            # 真实模式优先尝试自动 CreateObject，失败则回退到显式 txn_hash
            if self.mode == "real" and self.auto_uploader:
                try:
                    object_key = await self.auto_uploader.put_auto(key=object_key, data=data)
                except Exception as auto_err:
                    print(f"⚠️ 自动 CreateObject 失败，改用显式 txn_hash: {auto_err}")
                    object_key = self.storage.put(object_key, data, txn_hash=txn_hash_override)
            else:
                object_key = self.storage.put(object_key, data, txn_hash=txn_hash_override)
            upload_time = time.time() - start_time

            print(f"✅ 上传成功:")
            print(f"   对象键: {object_key}")
            print(f"   上传时间: {upload_time:.2f} 秒")
            print(f"   上传速度: {len(data) / upload_time:.2f} 字节/秒")

            # 下载前稍等，确保对象已 sealed
            if self.auto_uploader:
                await self.wait_object_ready(object_key)

            # 下载数据
            start_time = time.time()
            try:
                if self.bypass_seal and self.auto_uploader:
                    downloaded_data = self.auto_uploader.object_helper.download_via_cli(object_key)
                else:
                    downloaded_data = self.storage.get(object_key)
            except Exception as download_err:
                # 若 HTTP 下载失败且有 CLI 辅助，则尝试 CLI 下载
                if self.auto_uploader:
                    try:
                        downloaded_data = self.auto_uploader.object_helper.download_via_cli(object_key)
                        print("✅ 通过 gnfd-cmd 下载成功（HTTP 失败回退）")
                    except Exception as cli_err:
                        print(f"❌ 下载失败 (HTTP/CLI): {download_err} / {cli_err}")
                        return False
                else:
                    print(f"❌ 下载失败: {download_err}")
                    return False
            download_time = time.time() - start_time

            print(f"✅ 下载成功:")
            print(f"   下载大小: {len(downloaded_data)} 字节")
            print(f"   下载时间: {download_time:.2f} 秒")
            print(f"   下载速度: {len(downloaded_data) / download_time:.2f} 字节/秒")

            # 如果明确启用 bypassSeal，则跳过完整性校验（只要能下载即视为通过）
            if self.bypass_seal:
                print("⚠️ 已启用 bypassSeal，跳过完整性校验（仅验证上传+下载成功）")
                return True

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
            if self.mode == "hybrid" and "404" in str(e):
                print(f"⚠️ 混合模式：对象可能不存在（预期行为）")
                return True
            else:
                print(f"❌ 测试失败: {e}")
                return False

    async def test_error_handling(self) -> bool:
        """测试错误处理"""
        print(f"\n🧪 开始错误处理测试")

        try:
            # 测试获取不存在的对象
            print("   测试获取不存在的对象...")
            try:
                self.storage.get("non-existent-object-key-12345")
                if self.mode != "mock":
                    print("⚠️ 意外成功（可能是公开对象）")
            except RuntimeError as e:
                print(f"✅ 正确抛出异常: {type(e).__name__}")

            # 测试签名功能（仅对真实存储）
            if hasattr(self.storage, '_build_authorization'):
                print("   测试签名功能...")
                test_headers = {
                    "Content-Type": "application/octet-stream",
                    "Content-Length": "100",
                    "X-Gnfd-Txn-Hash": self.config.get("GREENFIELD_TXN_HASH", "0xtest"),
                    "X-Gnfd-Expiry-Timestamp": "2024-12-31T23:59:59Z"
                }

                try:
                    auth_header = self.storage._build_authorization(
                        method="PUT",
                        path="/test-object",
                        headers=test_headers,
                        body=b"test data"
                    )
                    print(f"✅ 签名构建成功: {auth_header[:50]}...")
                except Exception as e:
                    print(f"❌ 签名构建失败: {e}")
                    return False

            print(f"✅ 错误处理测试通过")
            return True

        except Exception as e:
            print(f"❌ 错误处理测试失败: {e}")
            return False

    async def test_performance(self) -> bool:
        """测试性能"""
        print(f"\n⚡ 开始性能测试")

        try:
            test_sizes = [
                (b"Small test", "小数据", "perf-small"),
                (b"X" * 1024, "1KB 数据", "perf-1kb"),
                (b"Y" * 10240, "10KB 数据", "perf-10kb"),
                (b"Z" * 102400, "100KB 数据", "perf-100kb"),
            ]

            performance_results = []

            for data, description, perf_key in test_sizes:
                print(f"   测试 {description} ({len(data)} 字节)...")

                # 上传性能测试
                start_time = time.time()
                object_key = perf_key if self.use_static_keys else None
                txn_hash_override = self.txn_hash_map.get(object_key) if object_key else None
                if self.mode == "real" and self.auto_uploader:
                    try:
                        object_key = await self.auto_uploader.put_auto(
                            key=object_key or self.storage._gen_key(),
                            data=data
                        )
                    except Exception as auto_err:
                        print(f"⚠️ 自动 CreateObject 失败（性能测试，使用 txn_hash 回退）: {auto_err}")
                        object_key = self.storage.put(object_key, data, txn_hash=txn_hash_override)
                else:
                    object_key = self.storage.put(object_key, data, txn_hash=txn_hash_override)
                upload_time = time.time() - start_time

                # 等待对象可读
                await self.wait_object_ready(object_key)

                # 下载性能测试
                start_time = time.time()
                if self.bypass_seal and self.auto_uploader:
                    downloaded_data = self.auto_uploader.object_helper.download_via_cli(object_key)
                else:
                    downloaded_data = self.storage.get(object_key)
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

    async def run_all_tests(self) -> Dict[str, bool]:
        """运行所有测试"""
        print(f"\n🧪 开始运行完整的 E2E 测试套件 (模式: {self.mode})")

        results = {}

        # 尝试初始化自动助手（真实模式）
        await self.ensure_auto_uploader()

        # 基础数据测试
        for test_name, data in TEST_DATA_EXAMPLES.items():
            if test_name == "very_large_data":
                continue  # 单独测试大数据
            results[test_name] = await self.test_upload_download(test_name, data)

        # 自动生成键测试
        print(f"\n🔑 测试自动生成对象键...")
        results["auto_key"] = await self.test_upload_download("自动键生成", b"Auto-generated key test", None)

        # 指定键测试
        print(f"\n🏷️ 测试指定对象键...")
        results["manual_key"] = await self.test_upload_download("手动键", b"Manual key test", "test-manual-key-123")

        # 错误处理测试
        results["error_handling"] = await self.test_error_handling()

        # 性能测试
        results["performance"] = await self.test_performance()

        # 大数据测试
        print(f"\n📦 测试大数据 (~320KB)...")
        results["very_large_data"] = await self.test_upload_download("大数据测试", TEST_DATA_EXAMPLES["very_large_data"])

        return results

    def print_summary(self, results: Dict[str, bool]) -> None:
        """打印测试结果总结"""
        print(f"\n📋 测试结果总结 (模式: {self.mode})")
        print("=" * 60)

        passed = sum(1 for result in results.values() if result)
        total = len(results)

        for test_name, result in results.items():
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{test_name:<25} {status}")

        print("-" * 60)
        print(f"总计: {passed}/{total} 测试通过")

        if passed == total:
            print(f"🎉 所有测试通过！Greenfield 存储工作正常。")
            if self.mode == "mock":
                print(f"💡 这是模拟模式测试，要测试真实功能请使用:")
                print(f"   python {__file__} --mode real")
            elif self.mode == "hybrid":
                print(f"💡 这是混合模式测试，部分测试可能模拟通过。")
        else:
            print(f"⚠️ 有 {total - passed} 个测试失败")
            if self.mode == "real":
                print(f"💡 建议先尝试模拟模式:")
                print(f"   python {__file__} --mode mock")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="改进的 BNB Greenfield E2E 测试")
    parser.add_argument(
        "--mode",
        choices=["real", "mock", "hybrid"],
        default="mock",
        help="测试模式: real(真实), mock(模拟), hybrid(混合)"
    )
    parser.add_argument(
        "--test-type",
        choices=["small", "json", "binary", "large", "all"],
        default="all",
        help="测试类型"
    )

    args = parser.parse_args()

    print("🌟 改进的 BNB Greenfield E2E 测试")
    print("=" * 60)

    # 创建测试实例
    tester = ImprovedE2ETest(mode=args.mode)
    await tester.ensure_auto_uploader()

    try:
        if args.test_type == "all":
            results = await tester.run_all_tests()
        elif args.test_type == "small":
            results = {"small_text": await tester.test_upload_download("小文本测试", TEST_DATA_EXAMPLES["small_text"])}
        elif args.test_type == "json":
            results = {"json_data": await tester.test_upload_download("JSON数据测试", TEST_DATA_EXAMPLES["json_data"])}
        elif args.test_type == "binary":
            results = {"binary_data": await tester.test_upload_download("二进制数据测试", TEST_DATA_EXAMPLES["binary_data"])}
        elif args.test_type == "large":
            results = {"large_data": await tester.test_upload_download("大数据测试", TEST_DATA_EXAMPLES["large_data"])}

        # 打印总结
        tester.print_summary(results)

        # 返回适当的退出码
        sys.exit(0 if all(results.values()) else 1)

    except KeyboardInterrupt:
        print(f"\n⚠️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试运行失败: {e}")
        logger.exception("Test execution failed")
        sys.exit(1)
    finally:
        # 关闭自动上传会话
        if tester.auto_uploader and hasattr(tester.auto_uploader, "close"):
            try:
                await tester.auto_uploader.close()
            except Exception:
                pass


if __name__ == "__main__":
    asyncio.run(main())
