from enum import StrEnum


class Ticker(StrEnum):
    """Supported indexes; values match Deribit `index_name`."""

    BTC_USD = "btc_usd"
    ETH_USD = "eth_usd"
