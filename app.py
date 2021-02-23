import settings
import store
import time
from huobi.client.generic import GenericClient
from huobi.client.market import MarketClient
from huobi.client.account import AccountClient
from policies.bid import BidPolicy


def get_all_symbols():
    try:
        generic_client = GenericClient(url=settings.config['COMMON']['host'])
        symbols = generic_client.get_exchange_symbols()
        ret_val = {}

        for sym in symbols:
            ret_val[sym.symbol] = sym

        return ret_val
    except Exception as e:
        print(e)
        return None


def get_account():
    try:
        account_client = AccountClient(url=settings.config['COMMON']['host'], api_key=settings.config['ACCOUNT']['api_key'], secret_key=settings.config['ACCOUNT']['secret_key'])
        accounts = account_client.get_accounts()
        
        for account in accounts:
            if account.type == "spot":
                store.account = account
    except Exception as e:
        print(e)


def update_price(event):
    if event.tick:
        if event.tick.symbol in store.symbol_policies:
            policy = store.symbol_policies[event.tick.symbol]
            policy.push_data(event.tick.bid)


def error_handler(error):
    print('error', error)


def start_sub_price():
    try:
        client = MarketClient(url=settings.config['COMMON']['host'])
        client.sub_pricedepth_bbo(settings.config['COMMON']['symbols'], update_price, error_handler)
    except Exception as e:
        print('ERROR:', e)


if __name__ == '__main__':
    store.hbsymbols = get_all_symbols()
    get_account()

    if store.hbsymbols is None:
        print('Get symbols failed')
    else:
        print('Started')
    
    target_symbols = settings.config['COMMON']['symbols']
    for sym in target_symbols.split(','):
        policy = BidPolicy(sym)
        # policy.get_kline()
        # policy.sub_kline()
        store.symbol_policies[sym] = policy

    start_sub_price()

    while True:
        time.sleep(1)