# Base Sepolia ERC-8004 合约参考

来源：Blockscout 已验证源码，便于对照 BNB 版本实现。

## 地址
- Identity 代理: `0x8004AA63c570c570eBF15376c0dB199918BFe9Fb`
  - 实现: `0x5e9d388fb30af84cebb1c2c3ff726413f08e6835` → `IdentityRegistryUpgradeable.sol`
- Reputation 代理: `0x8004bd8daB57f14Ed299135749a5CB5c42d341BF`
  - 实现: `0xcc332a69642e29b8bf1ff4ace84702db804519c4` → `ReputationRegistryUpgradeable.sol`
- Validation 代理: `0x8004C269D0A5647E51E121FeB226200ECE932d55`
  - 实现: `0x657f5bc2c13f56708f4a5d300f01aad1dcd15040` → `ValidationRegistryUpgradeable.sol`
- 通用代理包装: `ERC1967Proxy.sol`（与以上三个代理源码一致，OZ 5.4 复用）

## 获取方式
- 通过 Blockscout API：`https://base-sepolia.blockscout.com/api?module=contract&action=getsourcecode&address=<addr>`。
- 以上四个文件已直接保存于本目录，便于比对/复用。
