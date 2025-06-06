import os
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی
load_dotenv()

# تنظیمات تلگرام
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# آدرس‌های کیف پول
solana_wallets_str = os.getenv("SOLANA_WALLETS", "")
SOLANA_WALLETS = [wallet.strip() for wallet in solana_wallets_str.split(",") if wallet.strip()]

# API Keys - به‌روزرسانی شده
API_KEYS = {
    "MORALIS": os.getenv("MORALIS_API_KEY", "FREE"),
    "COINGECKO": os.getenv("COINGECKO_API_KEY", "FREE"),
    "DEXSCREENER": os.getenv("DEXSCREENER_API_KEY", "FREE"),
    "AVE": os.getenv("AVE_API_KEY", "FREE"),
    "COINSTATS": os.getenv("COINSTATS_API_KEY", "FREE"),
    "CRYPTOCOMPARE": os.getenv("CRYPTOCOMPARE_API_KEY", "FREE"),
    "GECKOTERMINAL": os.getenv("GECKOTERMINAL_API_KEY", "FREE"),
    "HOLDERSCAN": os.getenv("HOLDERSCAN_API_KEY", "FREE"),  # جدید
}

# لینک‌های محصولات نارموون
NARMOON_DEX_LINK = "https://chatgpt.com/g/g-681e61f1baa88191bf50a82156694a79-narmoon-dex"
NARMOON_COIN_LINK = "https://chatgpt.com/g/g-681e68b8ccf08191b5e53b91b4f09c6e-narmoon-coin"
TUTORIAL_VIDEO_LINK = "https://www.youtube.com/watch?v=WjQzb7rBboM"

# Base URLs برای API ها - به‌روزرسانی شده
BASE_URLS = {
    "DEXSCREENER": "https://api.dexscreener.com",
    "GECKOTERMINAL": "https://api.geckoterminal.com/api/v2",
    "COINGECKO": "https://api.coingecko.com/api/v3",
    "MORALIS_SOLANA": "https://solana-gateway.moralis.io",
    "MORALIS_INDEX": "https://deep-index.moralis.io/api/v2.2",
    "AVE": "https://prod.ave-api.com/v2",
    "COINSTATS": "https://openapiv1.coinstats.app",
    "CRYPTOCOMPARE": "https://min-api.cryptocompare.com/data",
    "HOLDERSCAN": "https://api.holderscan.com/v0/sol",  # جدید
}
