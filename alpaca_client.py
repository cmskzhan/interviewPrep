import requests
from typing import Optional, List, Dict, Any, Union

class AlpacaMarketDataClient:
    """
    Client for Alpaca Market Data v2 API.
    Generated based on Postman Collection: Market_Data_v2_API.json
    """
    
    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://data.alpaca.markets"):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Apca-Api-Key-Id": api_key,
            "Apca-Api-Secret-Key": api_secret,
            "Content-Type": "application/json"
        }

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Helper method to make GET requests."""
        url = f"{self.base_url}{endpoint}"
        proxy = {
            "http": "http://127.0.0.1:3128",
            "https": "http://127.0.0.1:3128",
        }
        # Filter out None values from params
        if params:
            params = {k: v for k, v in params.items() if v is not None}
            
        response = requests.get(url, headers=self.headers, params=params, proxies=proxy, verify=False)
        response.raise_for_status()
        return response.json()

    # ==========================================
    # Stock Pricing Data API (v2)
    # ==========================================

    def get_stock_bars(self, symbol: str, timeframe: str, start: str, end: Optional[str] = None, 
                       limit: int = 1000, page_token: Optional[str] = None, 
                       feed: str = 'sip', adjustment: str = 'raw') -> Dict[str, Any]:
        """
        Get historical bars for a stock.
        """
        endpoint = f"/v2/stocks/{symbol}/bars"
        params = {
            "start": start,
            "end": end,
            "timeframe": timeframe,
            "limit": limit,
            "page_token": page_token,
            "feed": feed,
            "adjustment": adjustment
        }
        return self._get(endpoint, params)

    def get_stock_trades(self, symbol: str, start: str, end: Optional[str] = None, 
                         limit: int = 1000, page_token: Optional[str] = None, 
                         feed: str = 'sip') -> Dict[str, Any]:
        """
        Get historical trades for a stock.
        """
        endpoint = f"/v2/stocks/{symbol}/trades"
        params = {
            "start": start,
            "end": end,
            "limit": limit,
            "page_token": page_token,
            "feed": feed
        }
        return self._get(endpoint, params)

    def get_stock_quotes(self, symbol: str, start: str, end: Optional[str] = None, 
                         limit: int = 1000, page_token: Optional[str] = None, 
                         feed: str = 'sip') -> Dict[str, Any]:
        """
        Get historical quotes for a stock.
        """
        endpoint = f"/v2/stocks/{symbol}/quotes"
        params = {
            "start": start,
            "end": end,
            "limit": limit,
            "page_token": page_token,
            "feed": feed
        }
        return self._get(endpoint, params)

    def get_stock_snapshot(self, symbol: str, feed: str = 'sip') -> Dict[str, Any]:
        """
        Get snapshot for a stock.
        """
        endpoint = f"/v2/stocks/{symbol}/snapshot"
        params = {"feed": feed}
        return self._get(endpoint, params)

    def get_multi_stock_bars(self, symbols: List[str], timeframe: str, start: str, end: Optional[str] = None, 
                             limit: int = 1000, page_token: Optional[str] = None, 
                             feed: str = 'sip', adjustment: str = 'raw') -> Dict[str, Any]:
        """
        Get historical bars for multiple stocks.
        """
        endpoint = "/v2/stocks/bars"
        params = {
            "symbols": ",".join(symbols),
            "start": start,
            "end": end,
            "timeframe": timeframe,
            "limit": limit,
            "page_token": page_token,
            "feed": feed,
            "adjustment": adjustment
        }
        return self._get(endpoint, params)

    def get_multi_stock_trades(self, symbols: List[str], start: str, end: Optional[str] = None, 
                               limit: int = 1000, page_token: Optional[str] = None, 
                               feed: str = 'sip') -> Dict[str, Any]:
        """
        Get historical trades for multiple stocks.
        """
        endpoint = "/v2/stocks/trades"
        params = {
            "symbols": ",".join(symbols),
            "start": start,
            "end": end,
            "limit": limit,
            "page_token": page_token,
            "feed": feed
        }
        return self._get(endpoint, params)

    def get_multi_stock_quotes(self, symbols: List[str], start: str, end: Optional[str] = None, 
                               limit: int = 1000, page_token: Optional[str] = None, 
                               feed: str = 'sip') -> Dict[str, Any]:
        """
        Get historical quotes for multiple stocks.
        """
        endpoint = "/v2/stocks/quotes"
        params = {
            "symbols": ",".join(symbols),
            "start": start,
            "end": end,
            "limit": limit,
            "page_token": page_token,
            "feed": feed
        }
        return self._get(endpoint, params)

    def get_multi_stock_snapshots(self, symbols: List[str], feed: str = 'sip') -> Dict[str, Any]:
        """
        Get snapshots for multiple stocks.
        """
        endpoint = "/v2/stocks/snapshots"
        params = {
            "symbols": ",".join(symbols),
            "feed": feed
        }
        return self._get(endpoint, params)

    def get_latest_stock_trade(self, symbol: str, feed: str = 'sip') -> Dict[str, Any]:
        """
        Get the latest trade for a stock.
        """
        endpoint = f"/v2/stocks/{symbol}/trades/latest"
        params = {"feed": feed}
        return self._get(endpoint, params)

    def get_latest_stock_quote(self, symbol: str, feed: str = 'sip') -> Dict[str, Any]:
        """
        Get the latest quote for a stock.
        """
        endpoint = f"/v2/stocks/{symbol}/quotes/latest"
        params = {"feed": feed}
        return self._get(endpoint, params)

    # ==========================================
    # Meta Data API
    # ==========================================

    def get_meta_conditions(self, tick_type: str, tape: str = 'A') -> Dict[str, Any]:
        """
        Get condition codes.
        tick_type: 'trade' or 'quote'
        tape: 'A', 'B', or 'C'
        """
        endpoint = f"/v2/meta/conditions/{tick_type}"
        params = {"tape": tape}
        return self._get(endpoint, params)

    def get_meta_exchanges(self) -> Dict[str, Any]:
        """
        Get exchange codes.
        """
        endpoint = "/v2/meta/exchanges"
        return self._get(endpoint)

    # ==========================================
    # Crypto Pricing Data API (v1beta2 preferred)
    # ==========================================

    def get_crypto_trades(self, symbols: List[str], start: str, end: Optional[str] = None, 
                          limit: int = 1000, page_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Get historical trades for crypto (v1beta2).
        """
        endpoint = "/v1beta2/crypto/trades"
        params = {
            "symbols": ",".join(symbols),
            "start": start,
            "end": end,
            "limit": limit,
            "page_token": page_token
        }
        return self._get(endpoint, params)

    def get_crypto_quotes(self, symbols: List[str], start: str, end: Optional[str] = None, 
                          limit: int = 1000, page_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Get historical quotes for crypto (v1beta2).
        """
        endpoint = "/v1beta2/crypto/quotes"
        params = {
            "symbols": ",".join(symbols),
            "start": start,
            "end": end,
            "limit": limit,
            "page_token": page_token
        }
        return self._get(endpoint, params)

    def get_crypto_bars(self, symbols: List[str], timeframe: str, start: str, end: Optional[str] = None, 
                        limit: int = 1000, page_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Get historical bars for crypto (v1beta2).
        """
        endpoint = "/v1beta2/crypto/bars"
        params = {
            "symbols": ",".join(symbols),
            "timeframe": timeframe,
            "start": start,
            "end": end,
            "limit": limit,
            "page_token": page_token
        }
        return self._get(endpoint, params)

    def get_crypto_snapshots(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Get snapshots for crypto (v1beta2).
        """
        endpoint = "/v1beta2/crypto/snapshots"
        params = {"symbols": ",".join(symbols)}
        return self._get(endpoint, params)

    def get_latest_crypto_trades(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Get latest trades for crypto (v1beta2).
        """
        endpoint = "/v1beta2/crypto/latest/trades"
        params = {"symbols": ",".join(symbols)}
        return self._get(endpoint, params)

    def get_latest_crypto_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Get latest quotes for crypto (v1beta2).
        """
        endpoint = "/v1beta2/crypto/latest/quotes"
        params = {"symbols": ",".join(symbols)}
        return self._get(endpoint, params)

    def get_latest_crypto_bars(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Get latest bars for crypto (v1beta2).
        """
        endpoint = "/v1beta2/crypto/latest/bars"
        params = {"symbols": ",".join(symbols)}
        return self._get(endpoint, params)

    def get_latest_crypto_orderbooks(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Get latest orderbooks for crypto (v1beta2).
        """
        endpoint = "/v1beta2/crypto/latest/orderbooks"
        params = {"symbols": ",".join(symbols)}
        return self._get(endpoint, params)
    
    # v1beta1 endpoints (for those not in v1beta2 or specific single symbol endpoints if needed)
    # Note: v1beta2 supports multi-symbol which is generally preferred. 
    # Including XBBO from v1beta1 as it wasn't explicitly in v1beta2 list in the JSON for multi-symbol? 
    # Actually, let's check the JSON. XBBO is v1beta1 in the JSON.

    def get_latest_crypto_xbbo(self, symbol: str, exchanges: Optional[str] = None) -> Dict[str, Any]:
        """
        Get latest XBBO for crypto (v1beta1).
        """
        endpoint = f"/v1beta1/crypto/{symbol}/xbbo/latest"
        params = {"exchanges": exchanges}
        return self._get(endpoint, params)

    def get_crypto_meta_spreads(self) -> Dict[str, Any]:
        """
        Get crypto meta spreads (v1beta1).
        """
        endpoint = "/v1beta1/crypto/meta/spreads"
        return self._get(endpoint)

    # ==========================================
    # News API
    # ==========================================

    def get_news(self, symbols: Optional[List[str]] = None, start: Optional[str] = None, 
                 end: Optional[str] = None, limit: int = 50, sort: str = 'ASC', 
                 include_content: bool = True, exclude_contentless: bool = True, 
                 page_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Get news articles.
        """
        endpoint = "/v1beta1/news"
        params = {
            "symbols": ",".join(symbols) if symbols else None,
            "start": start,
            "end": end,
            "limit": limit,
            "sort": sort,
            "include_content": str(include_content).lower(),
            "exclude_contentless": str(exclude_contentless).lower(),
            "page_token": page_token
        }
        return self._get(endpoint, params)

if __name__ == "__main__":
    msci_data_client = AlpacaMarketDataClient(api_key="PKUHDFPCOWWRTNXONIXWJCCWGB", api_secret="Y3LybAFCTpZAWNKcC4CVgaTeydqZtwmAu2nmeWGquK9")
    print(msci_data_client.get_stock_bars(symbol="MSFT", timeframe="1D", start="2026-04-11T00:00:00Z"))
