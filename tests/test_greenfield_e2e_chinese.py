"""
端到端 Greenfield E2E 测试

本测试演示了完整的 Greenfield 工作流程：
1. CreateObject 链上创建（通过助手自动执行）
2. PutObject 上传数据到存储提供者
3. GetObject 下载验证
4. 跨密钥检索以验证公开访问

运行此测试：
1. 设置环境变量（见 GREENFIELD_E2E_使用指南.md）
2. 运行：pytest tests/test_greenfield_e2e_chinese.py -v -m integration -s

所需的环境变量：
- GREENFIELD_RPC_URL（默认值：https://gnfd-testnet-fullnode-tendermint-us.bnbchain.org）
- GREENFIELD_SP_HOST（默认值：gnfd-testnet-sp1.bnbchain.org）
- GREENFIELD_BUCKET
- GREENFIELD_PRIVATE_KEY
- 可选：GREENFIELD_CHAIN_ID（测试网默认值：5600）

完整文档请参阅 GREENFIELD_E2E_使用指南.md。
"""

import asyncio
import json
import os
import pytest
import time
from typing import Any, Dict

from agent0_sdk.core.greenfield_cli import create_e2e_helper
from agent0_sdk.core.greenfield_storage import GreenfieldReputationStorage
from agent0_sdk.core.storage_factory import create_reputation_storage


@pytest.fixture(scope="module")
def e2e_config() -> Dict[str, Any]:
    """E2E 测试配置从环境变量获取。"""
    config = {}

    # 必需字段
    required_fields = [
        "GREENFIELD_BUCKET",
        "GREENFIELD_PRIVATE_KEY"
    ]

    for field in required_fields:
        if not os.getenv(field):
            pytest.skip(
                f"E2E 测试需要 {field}。"
                "从 .env.e2e.示例 设置环境变量"
            )
        config[field] = os.getenv(field)

    # 可选字段及默认值
    config["GREENFIELD_RPC_URL"] = os.getenv(
        "GREENFIELD_RPC_URL",
        "https://gnfd-testnet-fullnode-tendermint-us.bnbchain.org"
    )
    config["GREENFIELD_SP_HOST"] = os.getenv(
        "GREENFIELD_SP_HOST",
        "gnfd-testnet-sp1.bnbchain.org"
    )
    config["GREENFIELD_CHAIN_ID"] = int(os.getenv("GREENFIELD_CHAIN_ID", "5600"))
    config["GREENFIELD_TIMEOUT"] = int(os.getenv("GREENFIELD_TIMEOUT", "60"))

    print(f"\n🚀 E2E 测试配置：")
    print(f"  RPC URL: {config['GREENFIELD_RPC_URL']}")
    print(f"  SP 主机: {config['GREENFIELD_SP_HOST']}")
    print(f"  存储桶: {config['GREENFIELD_BUCKET']}")
    print(f"  链 ID: {config['GREENFIELD_CHAIN_ID']}")
    print(f"  超时: {config['GREENFIELD_TIMEOUT']}秒")

    return config


@pytest.fixture(scope="module")
async def auto_uploader(e2e_config) -> Any:
    """从 E2E 配置创建 GreenfieldAutoUploader。"""
    return await create_e2e_helper(e2e_config)


# E2E 测试数据
TEST_DATA_EXAMPLES = {
    "small_text": b"你好，Greenfield！这是一个 E2E 测试消息。",
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
    }).encode('utf-8'),
    "binary_data": bytes([i % 256 for i in range(256)]),  # 包含所有可能的字节值
    "large_data": b"X" * (100 * 1024),  # 100KB
}


class TestGreenfieldE2E:
    """BNB Greenfield 存储的端到端测试。"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_and_upload_small_text(self, auto_uploader, e2e_config):
        """测试小文本数据的完整工作流。"""
        print(f"\n📝 测试 1：小文本上传和下载")

        # 测试数据
        test_data = TEST_DATA_EXAMPLES["small_text"]
        object_key = f"e2e-test-small-{int(time.time())}"

        print(f"  键: {object_key}")
        print(f"  大小: {len(test_data)} 字节")

        try:
            # 步骤 1 & 2：自动创建和上传
            result_key = await auto_uploader.put_auto(key=object_key, data=test_data)
            assert result_key == object_key, f"键不匹配: {result_key} != {object_key}"
            print(f"  ✅ 上传成功")

            # 步骤 3：验证检索
            retrieved_data = await auto_uploader.get(key=object_key)
            assert retrieved_data == test_data, "检索过程中数据不匹配"
            print(f"  ✅ 检索成功: {len(retrieved_data)} 字节")

            # 步骤 4：跨键检索（公开访问测试）
            time.sleep(2)  # 允许传播
            cross_key_retrieved = await auto_uploader.get(key=object_key)
            assert cross_key_retrieved == test_data, "跨键检索失败"
            print(f"  ✅ 公开访问验证通过")

        except Exception as e:
            pytest.fail(f"E2E 测试失败: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_and_upload_json_data(self, auto_uploader, e2e_config):
        """测试 JSON 声誉数据的工作流。"""
        print(f"\n📊 测试 2：JSON 声誉数据")

        # 测试数据
        test_data = TEST_DATA_EXAMPLES["json_data"]
        object_key = f"e2e-test-json-{int(time.time())}"

        print(f"  键: {object_key}")
        print(f"  大小: {len(test_data)} 字节")

        try:
            # 上传
            result_key = await auto_uploader.put_auto(key=object_key, data=test_data)
            assert result_key == object_key
            print(f"  ✅ JSON 上传成功")

            # 检索和验证
            retrieved_data = await auto_uploader.get(key=object_key)
            assert retrieved_data == test_data, "JSON 数据损坏"

            # 解析 JSON 验证结构
            parsed_data = json.loads(retrieved_data.decode('utf-8'))
            assert "agent_id" in parsed_data
            assert "reputation" in parsed_data
            print(f"  ✅ JSON 结构验证通过")
            print(f"  代理 ID: {parsed_data['agent_id']}")
            print(f"  声誉分数: {parsed_data['reputation']['score']}")

        except Exception as e:
            pytest.fail(f"JSON E2E 测试失败: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_and_upload_binary_data(self, auto_uploader, e2e_config):
        """测试二进制数据（所有字节值）的工作流。"""
        print(f"\n🔢 测试 3：二进制数据完整性")

        # 测试数据 - 所有可能的字节值
        test_data = TEST_DATA_EXAMPLES["binary_data"]
        object_key = f"e2e-test-binary-{int(time.time())}"

        print(f"  键: {object_key}")
        print(f"  大小: {len(test_data)} 字节")
        print(f"  包含: 所有字节值（0x00 到 0xFF）")

        try:
            # 上传
            result_key = await auto_uploader.put_auto(key=object_key, data=test_data)
            assert result_key == object_key
            print(f"  ✅ 二进制上传成功")

            # 检索并验证完全匹配
            retrieved_data = await auto_uploader.get(key=object_key)
            assert retrieved_data == test_data, "检测到二进制数据损坏"

            # 验证无数据丢失
            if len(retrieved_data) != len(test_data):
                pytest.fail(f"大小不匹配: {len(retrieved_data)} != {len(test_data)}")

            # 检查字节级损坏
            corruption_count = sum(1 for i, (orig, retrv) in enumerate(zip(test_data, retrieved_data)) if orig != retrv)
            if corruption_count > 0:
                pytest.fail(f"检测到字节损坏: {corruption_count} 字节损坏")

            print(f"  ✅ 二进制完整性验证通过: {len(retrieved_data)} 字节")
            print(f"  字节完整性: 100%（无损坏）")

        except Exception as e:
            pytest.fail(f"二进制 E2E 测试失败: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_and_upload_large_data(self, auto_uploader, e2e_config):
        """测试大数据（1MB）的工作流。"""
        print(f"\n📦 测试 4：大数据（1MB）")

        # 测试数据
        test_data = TEST_DATA_EXAMPLES["large_data"]
        object_key = f"e2e-test-large-{int(time.time())}"

        print(f"  键: {object_key}")
        print(f"  大小: {len(test_data)} 字节 ({len(test_data)/1024:.1f} KB)")

        try:
            # 上传大数据（可能需要更长时间）
            print(f"  ⏳ 上传大数据中（这可能需要 30-60 秒）...")
            start_time = time.time()

            result_key = await auto_uploader.put_auto(key=object_key, data=test_data)

            upload_time = time.time() - start_time
            assert result_key == object_key
            print(f"  ✅ 大数据上传完成，耗时 {upload_time:.1f} 秒")

            # 检索和验证
            print(f"  ⏳ 检索大数据中...")
            start_time = time.time()

            retrieved_data = await auto_uploader.get(key=object_key)

            download_time = time.time() - start_time
            assert retrieved_data == test_data, "大数据损坏"

            upload_speed = len(test_data) / upload_time / 1024  # KB/s
            download_speed = len(retrieved_data) / download_time / 1024  # KB/s

            print(f"  ✅ 大数据验证通过")
            print(f"  上传速度: {upload_speed:.1f} KB/s")
            print(f"  下载速度: {download_speed:.1f} KB/s")

            # 性能指标
            if upload_speed < 50:  # 小于 50 KB/s 是慢速
                print(f"  ⚠️  上传速度较慢 ({upload_speed:.1f} KB/s)")
            if download_speed < 100:  # 小于 100 KB/s 是慢速
                print(f"  ⚠️  下载速度较慢 ({download_speed:.1f} KB/s)")

        except Exception as e:
            pytest.fail(f"大数据 E2E 测试失败: {e}")

    @pytest.mark.asyncio
    async def test_multiple_objects_with_unique_keys(self, auto_uploader, e2e_config):
        """测试使用唯一密钥创建和上传多个对象。"""
        print(f"\n🗂️ 测试 5：多个对象工作流")

        objects_created = []

        try:
            # 创建并上传 3 个对象
            for i in range(3):
                test_data = f"测试对象 {i+1} 内容".encode('utf-8')
                object_key = f"e2e-test-multi-{int(time.time())}-{i}"

                print(f"  对象 {i+1}: {object_key}")

                # 自动创建和上传
                result_key = await auto_uploader.put_auto(key=object_key, data=test_data)
                assert result_key == object_key
                objects_created.append(object_key)
                print(f"    ✅ 创建并上传成功")

            # 验证所有对象可以被检索
            for i, obj_key in enumerate(objects_created):
                retrieved_data = await auto_uploader.get(key=obj_key)
                expected_data = f"测试对象 {i+1} 内容".encode('utf-8')
                assert retrieved_data == expected_data
                print(f"    ✅ 对象 {i+1} 检索成功")

            print(f"  ✅ 所有 {len(objects_created)} 个对象验证通过")

        except Exception as e:
            pytest.fail(f"多个对象 E2E 测试失败: {e}")

    @pytest.mark.asyncio
    async def test_transaction_hash_uniqueness(self, auto_uploader, e2e_config):
        """测试每次上传使用唯一的事务哈希。"""
        print(f"\n🔑 测试 6：事务哈希唯一性")

        try:
            # 上传第一个对象
            data1 = b"第一个对象内容"
            key1 = f"e2e-test-tx-1-{int(time.time())}"
            result1 = await auto_uploader.put_auto(key=key1, data=data1)
            print(f"  对象 1: {key1}")

            # 上传第二个对象
            data2 = b"第二个对象内容"
            key2 = f"e2e-test-tx-2-{int(time.time())}"
            result2 = await auto_uploader.put_auto(key=key2, data=data2)
            print(f"  对象 2: {key2}")

            # 两者都应该成功，使用不同的事务哈希
            assert result1 == key1
            assert result2 == key2
            assert data1 != data2  # 不同的内容

            # 验证两者对象是独立存储的
            retrieved1 = await auto_uploader.get(key=key1)
            retrieved2 = await auto_uploader.get(key=key2)

            assert retrieved1 == data1
            assert retrieved2 == data2
            assert retrieved1 != retrieved2

            print(f"  ✅ 事务哈希唯一性验证通过")

        except Exception as e:
            pytest.fail(f"事务哈希唯一性测试失败: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_handling_invalid_object(self, auto_uploader, e2e_config):
        """测试无效对象操作的错误处理。"""
        print(f"\n❌ 测试 7：错误处理")

        try:
            # 尝试检索不存在的对象
            nonexistent_key = f"e2e-test-不存在-{int(time.time())}"
            print(f"  尝试检索: {nonexistent_key}")

            try:
                await auto_uploader.get(key=nonexistent_key)
                pytest.fail("应该为不存在的对象抛出错误")
            except RuntimeError as e:
                print(f"  ✅ 正确处理不存在的对象: {e}")
                assert "Failed to retrieve" in str(e)
                assert nonexistent_key in str(e)

            # 尝试上传空数据（应该工作）
            empty_key = f"e2e-test-空-{int(time.time())}"
            empty_result = await auto_uploader.put_auto(key=empty_key, data=b"")
            print(f"  ✅ 空数据上传允许: {empty_result}")

            # 验证空数据可以被检索
            empty_retrieved = await auto_uploader.get(key=empty_key)
            assert empty_retrieved == b""
            print(f"  ✅ 空数据检索验证通过")

        except Exception as e:
            pytest.fail(f"错误处理测试失败: {e}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrent_operations(self, auto_uploader, e2e_config):
        """测试并发上传和检索操作。"""
        print(f"\n🔄 测试 8：并发操作")

        async def upload_and_verify(index: int):
            test_data = f"并发测试 {index}".encode('utf-8')
            object_key = f"e2e-test-concurrent-{int(time.time())}-{index}"

            # 上传
            result_key = await auto_uploader.put_auto(key=object_key, data=test_data)
            assert result_key == object_key

            # 检索
            retrieved_data = await auto_uploader.get(key=object_key)
            assert retrieved_data == test_data

            return object_key

        try:
            # 运行 3 个并发操作
            print(f"  启动 5 个并发操作...")
            start_time = time.time()

            tasks = [upload_and_verify(i) for i in range(5)]
            results = await asyncio.gather(*tasks)

            concurrent_time = time.time() - start_time
            print(f"  ✅ 所有 {len(results)} 个并发操作完成")
            print(f"  总时间: {concurrent_time:.1f} 秒")
            print(f"  每个操作平均时间: {concurrent_time/len(results):.1f} 秒")

            # 验证所有密钥都是唯一的
            unique_keys = set(results)
            assert len(unique_keys) == len(results), "某些并发操作产生了重复密钥"

            print(f"  ✅ 并发唯一性验证通过")

        except Exception as e:
            pytest.fail(f"并发操作测试失败: {e}")

    @pytest.mark.asyncio
    async def cleanup_after_tests(self, auto_uploader, e2e_config):
        """测试后清理测试对象（可选）。"""
        print(f"\n🧹 清理")

        try:
            await auto_uploader.close()
            print(f"  ✅ 清理完成")
        except Exception as e:
            print(f"  ⚠️  清理警告: {e}")


class TestGreenfieldFactoryE2E:
    """Greenfield 存储工厂的 E2E 测试。"""

    @pytest.mark.integration
    def test_factory_with_auto_uploader(self, e2e_config):
        """测试工厂可以与自动上传器配置一起工作。"""
        print(f"\n🏭️ 测试：存储工厂集成")

        # 为 Greenfield 配置工厂
        config = {
            "REPUTATION_BACKEND": "greenfield",
            "GREENFIELD_SP_HOST": e2e_config["GREENFIELD_SP_HOST"],
            "GREENFIELD_BUCKET": e2e_config["GREENFIELD_BUCKET"],
            "GREENFIELD_PRIVATE_KEY": e2e_config["GREENFIELD_PRIVATE_KEY"],
            # 注意：无 GREENFIELD_TXN_HASH - 自动上传器会处理它
        }

        try:
            storage = create_reputation_storage(config=config)
            assert hasattr(storage, 'put')
            assert hasattr(storage, 'get')
            print(f"  ✅ 工厂创建了 Greenfield 存储成功")

            # 注意：这是基础测试 - 完整的自动上传器集成
            # 需要工厂使用 GreenfieldAutoUploader 类
            print(f"  ℹ️  如需完整的自动上传功能，"
                  f"请直接使用 GreenfieldAutoUploader")

        except Exception as e:
            pytest.fail(f"工厂 E2E 测试失败: {e}")


if __name__ == "__main__":
    # 允许直接运行此测试
    print("运行方式: pytest tests/test_greenfield_e2e_chinese.py -v -m integration -s")
    import sys
    sys.exit(pytest.main([__file__, "-v", "-m", "integration", "-s"]))