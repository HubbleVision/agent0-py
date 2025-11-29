BNB Greenfield 声誉存储改造方案（ERC8004）

目标与约束
- 保留现有 IPFS 实现，新增 Greenfield 存储实现，可通过配置选择，默认继续用 IPFS。
- 上层业务代码尽量零改动：通过统一接口/工厂注入后端实现。
- 数据格式和键策略保持与 IPFS 一致，避免上层序列化变化。

总体设计
- 抽象接口：`ReputationStorage`（`put(key, data: bytes) -> str`，`get(key: str) -> bytes`）。
- 现有 IPFS 逻辑改为 `IpfsReputationStorage` 实现接口，逻辑不动，仅适配方法签名。
- 新增 `GreenfieldReputationStorage`，使用 Greenfield SDK/HTTP 完成 `put/get`。
- 工厂/初始化：`create_reputation_storage(config)` 按 `REPUTATION_BACKEND=ipfs|greenfield` 返回实例；默认 ipfs。
- 调用层改动：把直接 new IPFS 的位置替换为工厂输出（通常仅 1 处）。

配置方案
- 新增：`REPUTATION_BACKEND`（默认 ipfs）。
- Greenfield：`GREENFIELD_BUCKET`、`GREENFIELD_PRIVATE_KEY`（或 keystore+pass）、`GREENFIELD_SP_HOST`（如 gnfd-testnet-spX.bnbchain.org）、`GREENFIELD_TXN_HASH`（CreateObject 返回的 Txn Hash，用于 PutObject）。如需链上查询，可额外提供 `GREENFIELD_ENDPOINT`/`GREENFIELD_CHAIN_ID`（可选）。
- IPFS：沿用现有 `IPFS_API_URL`、`IPFS_GATEWAY_URL`、`IPFS_PROJECT_ID/SECRET` 等，不变。

Greenfield 主要功能与文档入口
- 对象存储（桶/对象，S3 类似）：https://docs.bnbchain.org/bnb-greenfield/core-concept/data-storage/simple-storage-service/
- 访问控制（ACL/策略、跨链访问控制示例）：https://docs.bnbchain.org/bnb-greenfield/for-developers/tutorials/access-control/cmd-access-control/ 和 https://docs.bnbchain.org/bnb-greenfield/for-developers/tutorials/access-control/cross-chain-access-control-by-cmd/
- 跨链镜像（Greenfield <-> BSC 镜像概念与接口）：https://docs.bnbchain.org/bnb-greenfield/for-developers/cross-chain-integration/mirror-concept/
- 网络入口与节点信息（测试网/主网 RPC、SP 端点）：https://docs.bnbchain.org/bnb-greenfield/for-developers/network-endpoint/endpoints/
- API 与 SDK（JS/Go，含 REST/gRPC 指南）：https://docs.bnbchain.org/bnb-greenfield/for-developers/apis-and-sdks/、https://docs.bnbchain.org/bnb-greenfield/for-developers/apis-and-sdks/sdk-js/、https://docs.bnbchain.org/bnb-greenfield/for-developers/apis-and-sdks/sdk-go/
- 存储服务供应商标准（SP 行为规范/HTTP 接口概览）：https://docs.bnbchain.org/bnb-greenfield/storage-provider/standard/
- 计费与支付模型（Gas、存储费用、带宽结算）：https://docs.bnbchain.org/bnb-greenfield/core-concept/billing-payment/

本项目声誉层使用的 Greenfield 功能
- 仅使用对象存储能力：通过 SP HTTP API 的 `PutObject/GetObject`（对应“对象存储”与“SP 标准”章节）上传/读取声誉数据。
- 不依赖跨链镜像、ACL 高阶能力或支付模块的额外特性；如需访问控制，可后续结合 ACL/策略接口。

环境与密钥
- 测试网 vs 主网：测试网有独立的 chainId、SP 域名（如 `gnfd-testnet-sp*.bnbchain.org`）、RPC/全节点与水龙头；主网使用主网 SP 域名与链参数。配置项隔离即可无缝切换：更换 `GREENFIELD_SP_HOST`、`GREENFIELD_CHAIN_ID`、`GREENFIELD_ENDPOINT`、`GREENFIELD_BUCKET`、`GREENFIELD_TXN_HASH`（需重新在目标网络执行 CreateObject 获取）。
- 开发/测试：可在测试网创建 bucket/object 并获取 Txn Hash，验证读写；上线前需在主网重新创建 bucket 与对象（测试网数据不会自动迁移）。
- 获取密钥：
  - 使用 EVM 钱包生成私钥/keystore（如 MetaMask 导出私钥或 keystore 文件）。
  - 测试网 BNB 通过官方水龙头获取：https://docs.bnbchain.org/bnb-greenfield/getting-started/get-test-bnb/
  - 主网需自备 BNB 以支付 Gas/存储费用。
  - 配置时通过环境变量注入 `GREENFIELD_PRIVATE_KEY`（或 keystore+pass），避免写入代码仓库。
- 客户端下载方式：
  - 公共对象可直接使用 HTTP GET：`https://<bucket>.<sp_host>/<object>`（或 path-style），若 ACL 允许公开读则无需签名。
  - 受限对象需带 Authorization 头或使用服务端生成的签名 URL（可在后续扩展“获取下载 URL”能力）。
  - 前端/第三方可复用同样的 URL；若对象公开读，可直接浏览器下载；若需鉴权，可由后端签名后下发临时 URL。

接口调用注意（对照官方 `PutObject` 文档 https://github.com/bnb-chain/greenfield-storage-provider/blob/master/docs/storage-provider-rest-api/put_object.md）
- 请求需走虚拟域名或 path-style：`https://<bucket>.<sp_host>/<object>` 或 `https://<sp_host>/<bucket>/<object>`。
- 头：`Authorization`（按 README 的签名格式：https://github.com/bnb-chain/greenfield-storage-provider/blob/master/docs/storage-provider-rest-api/README.md#authorization-header）、`X-Gnfd-Txn-Hash`（链上 Txn Hash），可选 `Content-Type`、`Content-Length`。
- 方法：`PUT`，Body 为原始二进制；无 query（除 delegate 模式）。
- 响应：`200`，头含 `Etag` 与 `X-Gnfd-Request-ID`。
  - `X-Gnfd-Txn-Hash` 应来自链上创建对象/授权步骤；可参考官方创建对象/授权流程。

依赖与封装
- 官方文档入口：https://docs.bnbchain.org/bnb-greenfield/for-developers/get-started-dev/；官方目前无 Python SDK，主要提供 JS SDK 和 REST/gRPC 说明。
- Python 侧建议使用 HTTP/SP API + 签名实现，新增依赖：`requests>=2.31.0`、`eth-account>=0.9.0`（或 `web3>=6` 以便签名 EIP-712）。
- 如果后续出现官方 Python SDK，可在 `greenfield_storage.py` 内切换实现，不影响调用层。
- 将 Greenfield 依赖封装在 `greenfield_storage.py`，避免侵入其他模块；IPFS 文件仅小改以实现接口。
- 对外暴露统一的 `create_reputation_storage` 工厂，便于切换与测试。

实现步骤（最小改动路径）
1) 定义接口：新增 `interfaces.py`（或在现有模块中）声明 `ReputationStorage` 抽象类。
2) 适配 IPFS：在现 IPFS 客户端文件中实现接口，方法名对齐 `put/get`，内部逻辑保持不变。
3) 新增 Greenfield 实现：`greenfield_storage.py` 内注入 `sp_host`、`bucket`、`private_key`、`txn_hash`，构造 Authorization 头并调用 `PUT https://{bucket}.{sp_host}/{object}`；object key 可用现有哈希/CID 兼容。
4) 工厂与装配：新增/修改工厂函数（如 `create_reputation_storage(config)`），在唯一注入点替换为工厂返回值；若有依赖注入容器，增加绑定。
5) 配置与文档：新增环境变量说明；保持默认 IPFS，日志打印当前后端。
6) 测试：补充接口单测（stub IPFS/Greenfield 客户端）；集成测试在测试 bucket 上跑一次上传/下载；验证切换后业务逻辑不变。

数据与安全
- 数据序列化沿用现格式（JSON/bytes）；键使用现有 CID/哈希以便两端对齐。
- 私钥/keystore 仅通过环境变量或外部密钥管理传入，不落盘；如需访问控制，优先公开读、写需签名的最小策略。

回滚与兼容
- 默认 IPFS，不改现有部署；配置切回 `REPUTATION_BACKEND=ipfs` 即回退。
- 若 Greenfield 不可用，捕获异常并明确日志，避免影响 IPFS 流程。

关键代码片段（示例，最小改动导向）
- 接口定义（新增文件或现模块追加）：
```python
# interfaces.py
from abc import ABC, abstractmethod

class ReputationStorage(ABC):
    @abstractmethod
    def put(self, key: str, data: bytes) -> str: ...

    @abstractmethod
    def get(self, key: str) -> bytes: ...
```

- IPFS 适配（保持逻辑不变，仅实现接口）：
```python
# ipfs_storage.py（现有文件轻改）
class IpfsReputationStorage(ReputationStorage):
    def __init__(self, client):
        self.client = client  # 复用原有 IPFS client

    def put(self, key: str, data: bytes) -> str:
        # 原有上传逻辑，返回 CID
        return self.client.add_bytes(data)

    def get(self, key: str) -> bytes:
        # 原有下载逻辑
        return self.client.cat(key)
```

- Greenfield 实现（新增）：
```python
# greenfield_storage.py
import os
import requests
from eth_account import Account

class GreenfieldReputationStorage(ReputationStorage):
    def __init__(self, sp_host, bucket, private_key, txn_hash, content_type="application/octet-stream"):
        self.bucket = bucket
        self.sp_host = sp_host  # 例如 gnfd-testnet-spX.bnbchain.org
        self.account = Account.from_key(private_key)
        self.txn_hash = txn_hash  # 链上 CreateObject 得到的 Txn Hash，用于 PutObject 头
        self.content_type = content_type
        self.session = requests.Session()

    def put(self, key: str, data: bytes) -> str:
        object_key = key or self._gen_key()
        url = f"https://{self.bucket}.{self.sp_host}/{object_key}"  # virtual-hosted-style
        headers = {
            "Authorization": self._build_authorization(url, data),  # 按 README 的签名格式
            "X-Gnfd-Txn-Hash": self.txn_hash,
            "Content-Type": self.content_type,
            "Content-Length": str(len(data)),
        }
        resp = self.session.put(url, headers=headers, data=data, timeout=30)
        resp.raise_for_status()
        return object_key

    def get(self, key: str) -> bytes:
        url = f"https://{self.bucket}.{self.sp_host}/{key}"
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.content

    def _gen_key(self) -> str:
        import uuid
        return uuid.uuid4().hex

    def _build_authorization(self, url: str, data: bytes) -> str:
        # 占位：需按官方 README 的 Authorization 规则构造（签名 canonical request + headers + checksum/Txn Hash）。
        # 实际实现时应与 SDK/文档一致，以避免验签失败。
        return "TODO-signature"
```

- 工厂方法（在唯一注入点替换实例化）：
```python
# factory.py
import os

def create_reputation_storage(config=None) -> ReputationStorage:
    cfg = config or {}
    backend = cfg.get("REPUTATION_BACKEND") or os.getenv("REPUTATION_BACKEND", "ipfs")
    if backend == "greenfield":
        return GreenfieldReputationStorage(
            sp_host=cfg.get("GREENFIELD_SP_HOST") or os.getenv("GREENFIELD_SP_HOST"),
            bucket=cfg.get("GREENFIELD_BUCKET") or os.getenv("GREENFIELD_BUCKET"),
            private_key=cfg.get("GREENFIELD_PRIVATE_KEY") or os.getenv("GREENFIELD_PRIVATE_KEY"),
            txn_hash=cfg.get("GREENFIELD_TXN_HASH") or os.getenv("GREENFIELD_TXN_HASH"),
            # content_type 可选，默认 application/octet-stream
        )
    return IpfsReputationStorage(
        client=build_ipfs_client(cfg),  # 复用原有构建函数
    )
```

- 环境变量示例：
```bash
# 默认 IPFS
export REPUTATION_BACKEND=ipfs
export IPFS_API_URL=https://ipfs.infura.io:5001

# 切换到 Greenfield
export REPUTATION_BACKEND=greenfield
export GREENFIELD_BUCKET=hubble-reputation
export GREENFIELD_PRIVATE_KEY=0x...
export GREENFIELD_SP_HOST=gnfd-testnet-spX.bnbchain.org
export GREENFIELD_TXN_HASH=0x...   # CreateObject 得到的 Txn Hash
```
