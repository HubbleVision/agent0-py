#!/bin/bash
# Setup Node.js 20 LTS for Hardhat deployment

echo "=================================================="
echo "Node.js 20 LTS Setup for Hardhat"
echo "=================================================="

# Check current Node.js version
CURRENT_NODE=$(node --version)
echo "Current Node.js version: $CURRENT_NODE"

if [[ "$CURRENT_NODE" == v20.* ]]; then
    echo "✅ Node.js 20 already active!"
    exit 0
fi

echo ""
echo "Installing Node.js 20 LTS via Homebrew..."
echo ""

# Install node@20
brew install node@20

echo ""
echo "=================================================="
echo "⚠️  IMPORTANT: Temporary Node.js 20 Usage"
echo "=================================================="
echo ""
echo "To use Node.js 20 for this session, run:"
echo ""
echo "  export PATH=\"/opt/homebrew/opt/node@20/bin:\$PATH\""
echo ""
echo "Or add it to your shell profile for permanent use:"
echo ""
echo "  echo 'export PATH=\"/opt/homebrew/opt/node@20/bin:\$PATH\"' >> ~/.zshrc"
echo "  source ~/.zshrc"
echo ""
echo "Then verify:"
echo "  node --version  # Should show v20.x.x"
echo ""
echo "=================================================="
echo "Quick Deploy (one-time use):"
echo "=================================================="
echo ""
echo "  PATH=\"/opt/homebrew/opt/node@20/bin:\$PATH\" npx hardhat run scripts/deploy.js --network bnbTestnet"
echo ""
echo "=================================================="
