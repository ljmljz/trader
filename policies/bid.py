import store
import settings
import logging
import time
from threading import Thread
from queue import Queue
from datetime import datetime, timedelta
from huobi.constant.definition import CandlestickInterval, OrderType
from huobi.client.account import AccountClient
from huobi.client.trade import TradeClient


log = logging.getLogger()
INTERVAL = {
    1: CandlestickInterval.MIN1,
    5: CandlestickInterval.MIN5,
    15: CandlestickInterval.MIN15,
    30: CandlestickInterval.MIN30,
    60: CandlestickInterval.MIN60
}


class BidPolicy(Thread):
    def __init__(self, symbol):
        Thread.__init__(self, name=symbol + '_Bid_Policy')

        if symbol not in store.hbsymbols:
            self._symbol = None
        else:
            self._symbol = store.hbsymbols[symbol]

        self._name = symbol
        self._buy_in_price = 0.0
        self._buy_in = False
        self._sell_out = True
        self._money = 0
        self._amount = 0
        self._price = {"value": None, "timestamp": None}
        self._queue = Queue()
        self._account_client = AccountClient(url=settings.config['COMMON']['host'], api_key=settings.config['ACCOUNT']['api_key'], secret_key=settings.config['ACCOUNT']['secret_key'])
        self._trade_client = TradeClient(url=settings.config['COMMON']['host'], api_key=settings.config['ACCOUNT']['api_key'], secret_key=settings.config['ACCOUNT']['secret_key'])

        self.daemon = True
        self.start()

    def push_data(self, price):
        self._queue.put(price)

    def _get_balance(self, currency):
        balance = self._account_client.get_balance(store.account.id)
        for b in balance:
            if b.currency == currency and b.type == 'trade':
                return float(b.balance)
            
        return 0

    def run(self):
        while True:
            if not self._queue.empty():
                cur_time = datetime.now()
                cur_bid = self._queue.get()

                # print(self._name, cur_bid)

                if self._price['value'] is None:
                    self._price['value'] = cur_bid
                    self._price['timestamp'] = cur_time
                
                # print(datetime.now(), cur_bid, self._price['value'])

                diff = cur_time - self._price['timestamp']

                if not self._buy_in:
                    if diff.seconds < int(settings.config['COMMON']['interval']) * 60:
                        self._price['value'] = min(self._price['value'], cur_bid)
                    else:
                        if cur_bid <= self._price['value']:
                            # buy in 
                            self._money = self._get_balance('usdt') / len(store.symbol_policies)
                            print(self._money)
                            if self._money > 0:
                                self._amount = self._money / cur_bid

                                try:
                                    result = self._trade_client.create_spot_order(
                                        symbol=self.name, 
                                        account_id=store.account.id, 
                                        order_type=OrderType.BUY_MARKET, 
                                        amount=self._amount,
                                        price=None
                                    )

                                    if result != '':
                                        self._buy_in_price = cur_bid
                                        self._buy_in = True
                                        self._sell_out = False

                                        print(datetime.now(), 'buy in', cur_bid, self._amount, self._money)
                                        log.info("Buy in " + str(cur_bid) + ', ' + str(self._amount) + ', ' + str(self._money))
                                    else:
                                        print('Failed to buy in')
                                        log.info('Failed to buy in')
                                except Exception as e:
                                    print(e)
                        else:
                            self._price['value'] = min(self._price['value'], cur_bid)
                            self._price['timestamp'] = cur_time + timedelta(minutes=-int(settings.config['COMMON']['interval']))
                else:
                    stop_profit = float(settings.config['COMMON']['stop_profit'])
                    if cur_bid > (self._buy_in_price * stop_profit) and self._amount > 0:
                        # sell out
                        self._amount = self._get_balance(self._symbol.base_currency)
                        if self._amount > 0:
                            result = self._trade_client.create_spot_order(
                                symbol=self.name, 
                                account_id=store.account.id, 
                                order_type=OrderType.SELL_MARKET, 
                                amount=self._amount,
                                # price=cur_bid
                            )

                            if result != '':
                                self._buy_in = False
                                self._sell_out = True
                                self._price['value'] = cur_bid
                                self._price['timestamp'] = cur_time

                                print(datetime.now(), 'Sell out', cur_bid, self._amount, self._money)
                                log.info("Sell out " + str(cur_bid) + ', ' + str(self._amount) + ', ' + str(self._money))
            else:
                time.sleep(0.1)
