from datetime import datetime
from typing import List, Iterator, Optional, Tuple
from .models import Ticker, Resolution, NewOrder, Order, Symbol, Depth, Trade, Account, Ticker24

import requests
import json
import hmac


class APIError(RuntimeError):
    """
    General exception for API calls
    """

    operation: str  #: operation name
    code: int  #: HTTP response code
    text: str  #: error description

    def __init__(self, operation: str, code: int, text: str) -> None:
        self.code = code
        self.operation = operation
        self.text = text
        super().__init__('API ({}) error: code {}: {}'.format(operation, code, text))

    @staticmethod
    def ensure(operation: str, req: requests.Response):
        """
        Ensure status code of HTTP request and raise exception if needed

        :param operation: logical operation name
        :param req: request's response object
        """
        if req.status_code not in (200, 204):
            raise APIError(operation, req.status_code, req.text)


class Client:
    """
    HTTP client to the exchange for non-authorized requests.

    Supported environments:

    - 'mvp' - testnet sandbox with full-wipe each 2nd week (usually)
    - 'prod' - mainnet, production environment with real currency

    Disable `cache_market` if latest symbols info are always required
    """

    def __init__(self, *, env: str = 'mvp', cache_market: bool = True):
        self.environment = env
        if env == 'prod':
            self._base_url = 'https://crix.io'
        else:
            self._base_url = 'https://{}.crix.io'.format(env)
        self._base_url += '/api/v1'
        self.__cache_market = cache_market
        self.__market_cache = None
        self._session = requests.Session()

    def fetch_currency_codes(self) -> List[str]:
        """
        Get list of currencies codes in quote_base format (ex. btc_bch)

        :return: list of formatted currencies codes
        """
        return [(sym.base + "_" + sym.quote).lower() for sym in self.fetch_markets()]

    def fetch_markets(self, force: bool = False) -> Tuple[Symbol]:
        """
        Get list of all symbols on the exchange. Also includes symbol details like precision, quote, base and e.t.c.
        It's a good idea to cache result of this function after first invoke

        :param force: don't use cached symbols
        :return: list of supported symbols
        """
        if not self.__cache_market or force or self.__market_cache is None:
            symbols = []
            req = self._session.get(self._base_url + '/info/symbols')
            APIError.ensure('fetch-markets', req)
            data = req.json()
            for info in (data['symbol'] or []):
                symbols.append(Symbol.from_json(info))
            self.__market_cache = tuple(symbols)
        return self.__market_cache

    def fetch_order_book(self, symbol: str, level_aggregation: Optional[int] = None) -> Depth:
        """
        Get order book for specific symbol and level aggregation

        :param symbol: interesting symbol name
        :param level_aggregation: aggregate by rounding numbers (if not defined - no aggregation)
        :return: order depth book
        """
        req = {
            'symbolName': symbol
        }
        if level_aggregation is not None:
            req['levelAggregation'] = level_aggregation
        req = self._session.post(self._base_url + '/depths', json={
            'req': req
        })
        APIError.ensure('fetch-order-book', req)
        return Depth.from_json(req.json())

    def fetch_ticker(self) -> List[Ticker24]:
        """
        Get tickers for all symbols for the last 24 hours

        :return: list of tickers
        """
        tickers = []
        req = self._session.get(self._base_url + '/tickers24')
        APIError.ensure('ticker', req)
        data = req.json()
        for info in data['ohlc']:
            tickers.append(Ticker24.from_json(info))
        return tickers

    def fetch_ohlcv(self, symbol: str, utc_start_time: datetime, utc_end_time: datetime,
                    resolution: Resolution = Resolution.one_minute,
                    limit: int = 10) -> List[Ticker]:
        """
        Get K-Lines for specific symbol in a time frame

        :param symbol: K-Line symbol name
        :param utc_start_time: earliest interesting time
        :param utc_end_time: latest interesting time
        :param resolution: K-line resolution (by default 1-minute)
        :param limit: maximum number of entries in a response
        :return: list of ticker
        """
        tickers = []
        req = self._session.post(self._base_url + '/klines', json={
            'req': {
                'startTime': int(utc_start_time.timestamp() * 1000),
                'endTime': int(utc_end_time.timestamp() * 1000),
                'symbolName': symbol,
                'resolution': resolution.value,
                'limit': limit,
            }
        })
        APIError.ensure('fetch-ohlcv', req)
        data = req.json()
        for info in (data['ohlc'] or []):
            tickers.append(Ticker.from_json(info))
        return tickers


class AuthorizedClient(Client):
    """
    HTTP client to the exchange for non-authorized and authorized requests.

    Supported environments:

    - 'mvp' - testnet sandbox with full-wipe each 2nd week (usually)
    - 'prod' - mainnet, production environment with real currency

    Expects API token and API secret provided by CRIX.IO exchange as
    part of bot API.
    """

    def __init__(self, token: str, secret: str, *, env: str = 'mvp', cache_market: bool = True):
        super().__init__(env=env, cache_market=cache_market)
        self.__token = token
        self.__secret = secret

    def fetch_open_orders(self, *symbols: str, limit: int = 1000) -> Iterator[Order]:
        """
        Get all open orders for the user.

        .. note::
            One request per each symbol will be made plus additional
            request to query all supported symbols if symbols parameter
            not specified.


        :param symbols: filter orders by symbols. if not specified - all symbols queried and used
        :param limit: maximum number of orders for each symbol
        :return: iterator of orders definitions
        """
        if len(symbols) == 0:
            symbols = [sym.name for sym in self.fetch_markets()]
        for symbol in symbols:
            response = self.__signed_request('fetch-open-orders', self._base_url + '/user/orders/open', {
                'req': {
                    'limit': limit,
                    'symbolName': symbol
                }
            })
            for info in (response['orders'] or []):
                yield Order.from_json(info)

    def fetch_closed_orders(self, *symbols: str, limit: int = 1000) -> Iterator[Order]:
        """
        Get complete (filled, canceled) orders for user

        .. note::
            One request per each symbol will be made plus additional
            request to query all supported symbols if symbols parameter
            not specified.

        :param symbols: filter orders by symbols. if not specified - all symbols queried and used
        :param limit: maximum number of orders for each symbol
        :return: iterator of orders definitions
        """
        if len(symbols) == 0:
            symbols = [sym.name for sym in self.fetch_markets()]
        for symbol in symbols:
            response = self.__signed_request('fetch-closed-orders', self._base_url + '/user/orders/complete', {
                'req': {
                    'limit': limit,
                    'symbolName': symbol
                }
            })
            for info in (response['orders'] or []):
                yield Order.from_json(info)

    def fetch_orders(self, *symbols: str, limit: int = 1000) -> Iterator[Order]:
        """
        Get opened and closed orders filtered by symbols. If no symbols specified - all symbols are used.
        Basically the function acts as union of fetch_open_orders and fetch_closed_orders.

        .. note::
            Two requests per each symbol will be made plus additional
            request to query all supported symbols if symbols parameter
            not specified.

        :param symbols: symbols: filter orders by symbols. if not specified - used all symbols
        :param limit: maximum number of orders for each symbol for each state (open, close)
        :return: iterator of orders definitions sorted from open to close
        """
        if len(symbols) == 0:
            symbols = [sym.name for sym in self.fetch_markets()]
        for symbol in symbols:
            for order in self.fetch_open_orders(symbol, limit=limit):
                yield order
            for order in self.fetch_closed_orders(symbol, limit=limit):
                yield order

    def fetch_my_trades(self, *symbols: str, limit: int = 1000) -> Iterator[Trade]:
        """
        Get all trades for the user. There is some gap (a few ms) between time when trade is actually created and time
        when it becomes visible for the user.

        .. note::
            One request per each symbol will be made plus additional
            request to query all supported symbols if symbols parameter
            not specified.

        :param symbols: filter trades by symbols. if not specified - used all symbols
        :param limit: maximum number of trades for each symbol
        :return: iterator of trade definition
        """
        if len(symbols) == 0:
            symbols = [sym.name for sym in self.fetch_markets()]
        for symbol in symbols:
            response = self.__signed_request('fetch-my-trades', self._base_url + '/user/trades', {
                'req': {
                    'limit': limit,
                    'symbolName': symbol
                }
            })
            for info in (response['trades'] or []):
                yield Trade.from_json(info)

    def fetch_balance(self) -> List[Account]:
        """
        Get all balances for the user

        :return: list of all accounts
        """
        response = self.__signed_request('fetch-balance', self._base_url + '/user/accounts', {})
        return [Account.from_json(info) for info in (response['accounts'] or [])]

    def cancel_order(self, order_id: int, symbol: str) -> Order:
        """
        Cancel placed order

        :param order_id: order id generated by the exchange
        :param symbol: symbol names same as in placed order
        :return: order definition with filled field (also includes filled quantity)
        """
        response = self.__signed_request('cancel-order', self._base_url + '/user/order/cancel', {
            'req': {
                'orderId': order_id,
                'symbolName': symbol,
            }
        })
        return Order.from_json(response)

    def create_order(self, new_order: NewOrder) -> Order:
        """
        Create and place order to the exchange

        :param new_order: order parameters
        :return: order definition with filled fields from the exchange
        """
        response = self.__signed_request('create-order', self._base_url + '/user/order/create', {
            "req": new_order.to_json()
        })
        return Order.from_json(response)

    def fetch_order(self, order_id: int, symbol_name: str) -> Optional[Order]:
        """
        Fetch single open order info

        :param order_id: order id generated by server during 'create_order' phase
        :param symbol_name: symbol name same as in order
        :return: order definition or None if nothing found
        """
        try:
            response = self.__signed_request('fetch-order', self._base_url + '/user/order/info', {
                "req": {
                    "orderId": order_id,
                    "symbolName": symbol_name
                }
            })
        except APIError as err:
            if 'not found' in err.text:
                return None
            else:
                raise
        return Order.from_json(response)

    def fetch_history(self, begin: datetime, end: datetime, currency: str) -> Iterator[Ticker]:
        """
        Get historical minute tickers for specified time range and currency
        There are several caveats:

        - it requires additional permission
        - end param should be not more then server time, otherwise error returned
        - maximum difference between earliest and latest date should be no more then 366 days
        - it could be slow for a long time range
        - mostly all points have 1 minute tick however in a very few cases gap can be a bit bigger

        :param begin: earliest interesting time
        :param end: latest interesting time
        :param currency: currency name in upper case
        :return: iterator of parsed tickers
        """
        data = self.__signed_request('fetch-history', self._base_url + '/user/rates/history', {
            "req": {
                "currency": currency,
                "fromTimestamp": int(begin.timestamp()),
                "toTimestamp": int(end.timestamp())
            }
        })

        for info in data:
            yield Ticker.from_json_history(info)

    def __signed_request(self, operation: str, url: str, json_data: dict) -> dict:
        payload = json.dumps(json_data).encode()
        signer = hmac.new(self.__secret.encode(), digestmod='SHA256')
        signer.update(payload)
        signature = signer.hexdigest()
        headers = {
            'X-Api-Signed-Token': self.__token + ',' + signature,
        }
        req = self._session.post(url, data=payload, headers=headers)
        APIError.ensure(operation, req)
        return req.json()
