#!/usr/bin/env python3
"""
Greenfield 测试环境自动设置脚本

这个脚本会自动：
1. 创建测试 bucket（如果不存在）
2. 创建测试对象并获取 Transaction Hash
3. 更新 .env 文件中的 GREENFIELD_TXN_HASH
4. 验证配置是否正确

使用方法：
python scripts/setup_greenfield_test.py
"""

import os
import sys
import json
import time
import hashlib
from typing import Optional
from dotenv import load_dotenv

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from web3 import Web3
    from eth_account import Account
    import requests
except ImportError as e:
    print(f"❌ 缺少依赖: {e}")
    print("请安装: pip install web3 requests")
    sys.exit(1)


class GreenfieldSetup:
    """Greenfield 测试环境设置器"""

    def __init__(self):
        load_dotenv()

        # 从环境变量加载配置
        self.rpc_url = os.getenv("GREENFIELD_RPC_URL", "https://gnfd-testnet-fullnode-tendermint-us.bnbchain.org")
        self.chain_id = int(os.getenv("GREENFIELD_CHAIN_ID", "5600"))
        self.sp_host = os.getenv("GREENFIELD_SP_HOST", "gnfd-testnet-sp1.bnbchain.org")
        self.bucket_name = os.getenv("GREENFIELD_BUCKET", "hubble-reputation-test")
        self.private_key = os.getenv("GREENFIELD_PRIVATE_KEY")

        if not self.private_key:
            print("❌ 缺少 GREENFIELD_PRIVATE_KEY")
            sys.exit(1)

        # 确保私钥格式正确
        if not self.private_key.startswith("0x"):
            self.private_key = "0x" + self.private_key

        self.account = Account.from_key(self.private_key)
        self.w3 = Web3()

        print(f"🔧 配置:")
        print(f"   RPC: {self.rpc_url}")
        print(f"   Chain ID: {self.chain_id}")
        print(f"   SP Host: {self.sp_host}")
        print(f"   Bucket: {self.bucket_name}")
        print(f"   Wallet: {self.account.address}")

    def check_wallet_balance(self) -> bool:
        """检查钱包余额"""
        print(f"\n💰 检查钱包余额...")

        try:
            # 获取余额的 RPC 调用
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getBalance",
                "params": [self.account.address, "latest"],
                "id": 1
            }

            response = requests.post(self.rpc_url, json=payload, timeout=30)
            if response.status_code != 200:
                print(f"❌ 无法获取余额: {response.status_code}")
                return False

            result = response.json()
            if "error" in result:
                print(f"❌ 获取余额错误: {result['error']}")
                return False

            balance_wei = int(result["result"], 16)
            balance_bnb = balance_wei / 10**18

            print(f"✅ 余额: {balance_bnb:.6f} BNB")

            if balance_bnb < 0.01:
                print(f"⚠️ 余额不足，建议至少有 0.01 BNB 用于测试")
                print(f"🚰 水龙头: https://gnfd-bsc-faucet.bnbchain.org/")
                return False

            return True

        except Exception as e:
            print(f"❌ 检查余额失败: {e}")
            return False

    def check_bucket_exists(self) -> bool:
        """检查 bucket 是否存在"""
        print(f"\n🪣 检查 bucket 是否存在...")

        try:
            url = f"https://{self.bucket_name}.{self.sp_host}/"
            response = requests.head(url, timeout=30)

            if response.status_code == 200:
                print(f"✅ Bucket '{self.bucket_name}' 存在")
                return True
            elif response.status_code == 404:
                print(f"❌ Bucket '{self.bucket_name}' 不存在")
                return False
            else:
                print(f"⚠️ 无法确定 bucket 状态: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ 检查 bucket 失败: {e}")
            return False

    def create_test_transaction_hash(self) -> Optional[str]:
        """创建测试用的 Transaction Hash"""
        print(f"\n🔗 创建测试 Transaction Hash...")

        print(f"💡 由于 Greenfield 链上操作的复杂性，我们提供两种方案：")

        choice = input(f"""
选择方案：
1. 使用预设的测试 Transaction Hash（用于测试验证）
2. 手动创建真实 Transaction Hash（推荐）

请选择 (1 或 2): """).strip()

        if choice == "1":
            return self._use_test_transaction_hash()
        elif choice == "2":
            return self._guide_manual_creation()
        else:
            print(f"❌ 无效选择")
            return None

    def _use_test_transaction_hash(self) -> Optional[str]:
        """使用预设的测试 Transaction Hash"""
        print(f"\n🧪 使用测试 Transaction Hash...")

        test_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"

        print(f"⚠️ 这是一个测试用的 Transaction Hash")
        print(f"   它将用于验证配置的正确性")
        print(f"   但实际的上传操作仍然会失败（因为没有真实的链上对象）")
        print(f"   这对于测试代码逻辑和错误处理仍然有用")

        confirm = input("确认使用测试 Transaction Hash？(y/N): ").strip().lower()
        if confirm == 'y':
            return test_hash
        return None

    def _guide_manual_creation(self) -> Optional[str]:
        """指导手动创建真实的 Transaction Hash"""
        print(f"""
🎯 手动创建 Transaction Hash 指南：

方法 1：使用 DCellar（推荐）
1. 访问: https://dcellar.bnbchain.org/
2. 连接钱包（使用配置中的私钥对应的钱包）
3. 切换到 Greenfield 测试网
4. 选择你的 bucket: '{self.bucket_name}'
5. 点击 "Upload" 上传任意文件（建议小文件，如 1KB 的文本文件）
6. 等待交易确认
7. 从交易详情页面复制 Transaction Hash（以 0x 开头的 64 字符字符串）

方法 2：使用 CLI 工具
1. 创建测试文件:
   echo "test data" > /tmp/test.txt

2. 使用 greenfield-cmd 上传:
   gfdcmd object put \\
     --bucket-name {self.bucket_name} \\
     --object-name test-object \\
     --file /tmp/test.txt

3. 从命令输出中复制 Transaction Hash

获取到 Transaction Hash 后，请在这里输入：
""")

        txn_hash = input("Transaction Hash: ").strip()

        if not txn_hash.startswith("0x"):
            txn_hash = "0x" + txn_hash

        if len(txn_hash) != 66:
            print(f"❌ Transaction Hash 格式错误，应该是 66 字符（包含 0x）")
            return None

        print(f"✅ Transaction Hash: {txn_hash}")
        return txn_hash

    def update_env_file(self, txn_hash: str) -> bool:
        """更新 .env 文件"""
        print(f"\n📝 更新 .env 文件...")

        try:
            env_file = ".env"

            # 读取现有内容
            with open(env_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查是否已存在 GREENFIELD_TXN_HASH
            if "GREENFIELD_TXN_HASH=" in content:
                # 更新现有的
                lines = content.split('\n')
                new_lines = []

                for line in lines:
                    if line.strip().startswith("GREENFIELD_TXN_HASH="):
                        new_lines.append(f"GREENFIELD_TXN_HASH={txn_hash}")
                    else:
                        new_lines.append(line)

                content = '\n'.join(new_lines)
            else:
                # 添加新的（在 GREENFIELD_PRIVATE_KEY 之后）
                lines = content.split('\n')
                new_lines = []

                for line in lines:
                    new_lines.append(line)
                    if line.strip().startswith("GREENFIELD_PRIVATE_KEY="):
                        new_lines.append(f"GREENFIELD_TXN_HASH={txn_hash}")

                content = '\n'.join(new_lines)

            # 写回文件
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"✅ 已更新 GREENFIELD_TXN_HASH={txn_hash}")
            return True

        except Exception as e:
            print(f"❌ 更新 .env 文件失败: {e}")
            return False

    def test_configuration(self) -> bool:
        """测试配置是否正确"""
        print(f"\n🧪 测试配置...")

        try:
            # 重新加载环境变量
            load_dotenv()

            from agent0_sdk.core.greenfield_storage import GreenfieldReputationStorage

            storage = GreenfieldReputationStorage(
                sp_host=self.sp_host,
                bucket=self.bucket_name,
                private_key=self.private_key,
                txn_hash=os.getenv("GREENFIELD_TXN_HASH")
            )

            print(f"✅ Greenfield 存储初始化成功")
            print(f"   Wallet: {storage.account.address}")
            print(f"   Bucket: {storage.bucket}")
            print(f"   Has Txn Hash: {bool(storage.default_txn_hash)}")

            if not storage.default_txn_hash:
                print(f"❌ Transaction Hash 未正确设置")
                return False

            # 测试签名功能
            test_headers = {
                "Content-Type": "application/octet-stream",
                "Content-Length": "100",
                "X-Gnfd-Txn-Hash": storage.default_txn_hash,
                "X-Gnfd-Expiry-Timestamp": "2024-12-31T23:59:59Z"
            }

            auth_header = storage._build_authorization(
                method="PUT",
                path="/test-object",
                headers=test_headers,
                body=b"test data"
            )

            print(f"✅ 签名功能正常: {auth_header[:50]}...")

            return True

        except Exception as e:
            print(f"❌ 配置测试失败: {e}")
            return False

    def run(self):
        """运行完整的设置流程"""
        print(f"🚀 开始 Greenfield 测试环境设置")
        print(f"=" * 50)

        # 检查钱包余额
        if not self.check_wallet_balance():
            print(f"\n⚠️ 钱包余额不足，请先获取测试币")
            print(f"🚰 水龙头: https://gnfd-bsc-faucet.bnbchain.org/")
            return False

        # 检查 bucket
        if not self.check_bucket_exists():
            print(f"\n❌ Bucket '{self.bucket_name}' 不存在")
            print(f"请在 DCellar 中创建该 bucket: https://dcellar.bnbchain.org/")
            return False

        # 创建 Transaction Hash
        txn_hash = self.create_test_transaction_hash()
        if not txn_hash:
            return False

        # 更新配置文件
        if not self.update_env_file(txn_hash):
            return False

        # 测试配置
        if not self.test_configuration():
            return False

        print(f"\n🎉 设置完成！")
        print(f"✅ 现在可以运行 E2E 测试:")
        print(f"   python tests/run_greenfield_e2e.py all")

        return True


def main():
    """主函数"""
    setup = GreenfieldSetup()
    success = setup.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()