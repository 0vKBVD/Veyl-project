"""Central VEYL asset catalog used by market and prediction features."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Asset:
    coin_id: str
    symbol: str
    name: str
    binance_symbol: str


# Discord application-command choices are limited to 25 entries.
PREDICT_ASSETS = (
    Asset("bitcoin", "BTC", "Bitcoin", "BTCUSDT"),
    Asset("ethereum", "ETH", "Ethereum", "ETHUSDT"),
    Asset("binancecoin", "BNB", "BNB", "BNBUSDT"),
    Asset("solana", "SOL", "Solana", "SOLUSDT"),
    Asset("ripple", "XRP", "XRP", "XRPUSDT"),
    Asset("dogecoin", "DOGE", "Dogecoin", "DOGEUSDT"),
    Asset("cardano", "ADA", "Cardano", "ADAUSDT"),
    Asset("avalanche-2", "AVAX", "Avalanche", "AVAXUSDT"),
    Asset("chainlink", "LINK", "Chainlink", "LINKUSDT"),
    Asset("shiba-inu", "SHIB", "Shiba Inu", "SHIBUSDT"),
    Asset("tron", "TRX", "TRON", "TRXUSDT"),
    Asset("polkadot", "DOT", "Polkadot", "DOTUSDT"),
    Asset("litecoin", "LTC", "Litecoin", "LTCUSDT"),
    Asset("uniswap", "UNI", "Uniswap", "UNIUSDT"),
    Asset("sui", "SUI", "Sui", "SUIUSDT"),
    Asset("arbitrum", "ARB", "Arbitrum", "ARBUSDT"),
    Asset("optimism", "OP", "Optimism", "OPUSDT"),
    Asset("pepe", "PEPE", "Pepe", "PEPEUSDT"),
    Asset("bitcoin-cash", "BCH", "Bitcoin Cash", "BCHUSDT"),
    Asset("stellar", "XLM", "Stellar", "XLMUSDT"),
    Asset("near", "NEAR", "NEAR Protocol", "NEARUSDT"),
    Asset("cosmos", "ATOM", "Cosmos", "ATOMUSDT"),
    Asset("aptos", "APT", "Aptos", "APTUSDT"),
    Asset("internet-computer", "ICP", "Internet Computer", "ICPUSDT"),
    Asset("hedera-hashgraph", "HBAR", "Hedera", "HBARUSDT"),
)

ASSET_BY_ID = {asset.coin_id: asset for asset in PREDICT_ASSETS}
ASSET_BY_SYMBOL = {asset.symbol.lower(): asset for asset in PREDICT_ASSETS}


def get_asset(value: str) -> Asset | None:
    if not value:
        return None
    key = str(value).strip().lower()
    return ASSET_BY_ID.get(key) or ASSET_BY_SYMBOL.get(key)
