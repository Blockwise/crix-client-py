from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import NamedTuple, List, Optional, Union


class Symbol(NamedTuple):
    name: str
    base: str
    base_precision: int
    quote: str
    quote_precision: int
    description: str
    level_aggregation: List[int]
    maker_fee: Decimal
    taker_fee: Decimal
    min_lot: Decimal
    max_lot: Decimal
    min_price: Decimal
    max_price: Decimal
    min_notional: Decimal
    tick_lot: Decimal
    tick_price: Decimal
    is_trading: bool

    @staticmethod
    def from_json(info: dict) -> 'Symbol':
        """
        Construct object from dictionary
        """
        return Symbol(
            name=info['symbolName'],
            base=info['base'],
            base_precision=info['basePrecision'],
            quote=info['quote'],
            quote_precision=info['quotePrecision'],
            description=info['desc'],
            level_aggregation=info['levelAggregation'],
            maker_fee=Decimal(info['makerFee']),
            taker_fee=Decimal(info['takerFee']),
            min_lot=Decimal(info['minLot']),
            max_lot=Decimal(info['maxLot']),
            min_price=Decimal(info['minPrice']),
            max_price=Decimal(info['maxPrice']),
            min_notional=Decimal(info['minNotional']),
            tick_lot=Decimal(info['tickLot']),
            tick_price=Decimal(info['tickPrice']),
            is_trading=info['trading'],
        )


class Ticker(NamedTuple):
    symbol_name: str
    open_time: datetime
    open: Decimal  # type: Decimal
    close: Decimal
    high: Decimal
    low: Decimal
    volume: Decimal
    resolution: str

    @staticmethod
    def from_json(info: dict) -> 'Ticker':
        """
        Construct object from dictionary
        """
        return Ticker(
            symbol_name=info['symbolName'],
            open_time=datetime.fromtimestamp(info['openTime'] / 1000.0),
            open=Decimal(info['open']),
            close=Decimal(info['close']),
            high=Decimal(info['high']),
            low=Decimal(info['low']),
            volume=Decimal(info['volume']),
            resolution=info['resolution']
        )

    @staticmethod
    def from_json_history(info: dict) -> 'Ticker':
        """
        Construct object from dictionary (for a fixed resolution)
        """
        return Ticker(
            symbol_name=info['currency'],
            open_time=datetime.fromtimestamp(info['timestamp']),
            open=Decimal(str(info['open'])),
            close=Decimal(str(info['close'])),
            high=Decimal(str(info['high'])),
            low=Decimal(str(info['low'])),
            volume=Decimal(str(info['volume'])),
            resolution='D',
        )


class Ticker24(NamedTuple):
    symbol_name: str
    open_time: datetime
    open: Decimal
    close: Decimal
    high: Decimal
    low: Decimal
    volume: Decimal
    resolution: str
    # extended info
    first_id: int
    last_id: int
    prev_close_price: Decimal
    price_change: Decimal
    price_change_percent: Decimal

    @staticmethod
    def from_json(info: dict) -> 'Ticker24':
        """
        Construct object from dictionary
        """
        return Ticker24(
            symbol_name=info['symbolName'],
            open_time=datetime.fromtimestamp(info['openTime'] / 1000.0),
            open=Decimal(info['open']),
            close=Decimal(info['close']),
            high=Decimal(info['high']),
            low=Decimal(info['low']),
            volume=Decimal(info['volume']),
            resolution=info['resolution'],
            first_id=info['firstId'],
            last_id=info['lastId'],
            prev_close_price=Decimal(info['prevClosePrice'] or '0'),
            price_change=Decimal(info['priceChange'] or '0'),
            price_change_percent=Decimal(info['priceChangePercent'] or '0'),
        )


class Offer(NamedTuple):
    count: int
    price: Decimal
    quantity: Decimal

    @staticmethod
    def from_json(info: dict) -> 'Offer':
        """
        Construct object from dictionary
        """
        return Offer(
            count=info['c'],
            price=Decimal(info['p']),
            quantity=Decimal(info['q'])
        )


class Depth(NamedTuple):
    symbol_name: str
    is_aggregated: bool
    last_update_id: int
    level_aggregation: int
    asks: List[Offer]
    bids: List[Offer]

    @staticmethod
    def from_json(info: dict) -> 'Depth':
        """
        Construct object from dictionary
        """
        return Depth(
            symbol_name=info['symbolName'],
            level_aggregation=info['levelAggregation'],
            last_update_id=info['lastUpdateId'],
            is_aggregated=info['aggregated'],
            asks=[Offer.from_json(offer) for offer in (info['asks'] or [])],
            bids=[Offer.from_json(offer) for offer in (info['bids'] or [])],
        )


class Resolution(Enum):
    one_minute = '1'
    five_minutes = '5'
    fifteen_minutes = '15'
    half_an_hour = '30'
    hour = '60'
    two_hours = '120'
    four_hours = '240'
    day = 'D'
    week = 'W'


class TimeInForce(Enum):
    good_till_cancel = 0
    immediate_or_cancel = 1
    fill_or_kill = 2
    good_till_date = 3


class OrderStatus(Enum):
    new = 0
    complete = 1
    cancel = 2


class Order(NamedTuple):
    id: int
    user_id: int
    symbol_name: str
    is_buy: bool
    quantity: Decimal
    price: Decimal
    stop_price: Decimal
    filled_quantity: Decimal
    time_in_force: TimeInForce
    expire_time: Optional[datetime]
    status: OrderStatus

    @staticmethod
    def from_json(info: dict) -> 'Order':
        """
        Construct object from dictionary
        """
        return Order(
            id=info['orderId'],
            user_id=info['userId'],
            symbol_name=info['symbolName'],
            is_buy=info['isBuy'],
            quantity=Decimal(info['quantity'] or '0'),
            price=Decimal(info['price'] or '0'),
            stop_price=Decimal(info['stopPrice'] or '0'),
            filled_quantity=Decimal(info['filledQuantity'] or '0'),
            time_in_force=TimeInForce(info['timeInForce']),
            expire_time=datetime.fromtimestamp(info['expireTime'] / 1000) if info['expireTime'] and info[
                'expireTime'] > 0 else None,
            status=OrderStatus(info['status'])
        )


class NewOrder(NamedTuple):
    symbol: str
    price: Decimal
    quantity: Decimal
    is_buy: bool
    time_in_force: TimeInForce = TimeInForce.good_till_cancel
    stop_price: Optional[Decimal] = None
    expire_time: Optional[datetime] = None

    def to_json(self) -> dict:
        """
        Build JSON package ready to send to the API endpoint
        """
        req = {
            "isBuy": self.is_buy,
            "price": str(self.price),
            "quantity": str(self.quantity),
            "symbolName": self.symbol,
            "timeInForce": self.time_in_force.value,
        }
        if self.stop_price is not None:
            req["stopPrice"] = str(self.stop_price)
        if self.expire_time is not None:
            req["expireTime"] = int(self.expire_time.timestamp() * 1000)
        return req

    @staticmethod
    def limit(symbol: str, is_buy: bool, price: Union[Decimal, float, str], quantity: Union[Decimal, float, str],
              **args) -> 'NewOrder':
        """
        Helper to create basic limit order

        :param symbol: symbol name as defined by the exchange
        :param is_buy: order direction
        :param price: order price
        :param quantity: number of items in the order
        :param args: additional parameters proxied to the NewOrder constructor
        :return: new order
        """
        return NewOrder(symbol=symbol,
                        price=Decimal(price),
                        quantity=Decimal(quantity),
                        is_buy=is_buy,
                        **args)

    @staticmethod
    def market(symbol: str, is_buy: bool, quantity: Union[Decimal, float, str], **args) -> 'NewOrder':
        """
        Helper to create basic market order

        :param symbol: symbol name as defined by the exchange
        :param is_buy: order direction
        :param quantity: number of items
        :param args: additional parameters proxied to the NewOrder constructor
        :return: new order
        """
        return NewOrder(symbol=symbol,
                        price=Decimal('0'),
                        quantity=Decimal(quantity),
                        is_buy=is_buy,
                        time_in_force=TimeInForce.immediate_or_cancel,
                        **args)


class Trade(NamedTuple):
    id: int
    created_at: datetime
    buy_user_id: int
    buy_order_id: int
    is_buy_order_filled: bool
    sell_user_id: int
    sell_order_id: int
    is_sell_order_filled: bool

    is_buy: bool
    order_id: int
    price: Decimal
    quantity: Decimal
    fee: Decimal
    fee_currency: str
    symbol_name: str

    @staticmethod
    def from_json(info: dict) -> 'Trade':
        """
        Construct object from dictionary
        """
        return Trade(
            id=info['id'],
            created_at=datetime.fromtimestamp(info['createdAt'] / 1000),
            buy_user_id=info['buyUserId'],
            buy_order_id=info['buyOrderId'],
            is_buy_order_filled=info['buyOrderFilled'],
            sell_user_id=info['sellUserId'],
            sell_order_id=info['sellOrderId'],
            is_sell_order_filled=info['sellOrderFilled'],
            is_buy=info['isBuy'],
            order_id=info['orderId'],
            price=Decimal(info['price']),
            quantity=Decimal(info['quantity']),
            fee=Decimal(info['fee'] or '0'),
            fee_currency=info['feeCurrency'],
            symbol_name=info['symbolName'],
        )


class Account(NamedTuple):
    id: int
    user_id: int
    balance: Decimal
    locked_balance: Decimal
    currency_name: str
    deposit_address: str

    @staticmethod
    def from_json(info: dict) -> 'Account':
        """
        Construct object from dictionary
        """
        return Account(
            id=info['id'],
            user_id=info['userId'],
            balance=Decimal(info['balance'] or '0'),
            locked_balance=Decimal(info['lockedBalance'] or '0'),
            currency_name=info['currencyName'],
            deposit_address=info['depositAddress']
        )
