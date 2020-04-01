import json
import arrow
import td_ameritrade_api as td
from .tda_connect import connect_to_tda
from .pyjson import PyJSON


def decode_tda_symbol(td_sym):
    # Example: "FAS_040320C28"
    delim = td_sym.find('_')
    underlying = td_sym[0:delim]
    exp_mo = td_sym[delim+1:delim+3]
    exp_day = td_sym[delim+3:delim+5]
    exp_yr = td_sym[delim+5:delim+7]
    asset_char = td_sym[delim+7:delim+8]
    strike_str = td_sym[delim+8:]

    exp = arrow.Arrow(year=2000 + int(exp_yr), month=int(exp_mo), day=int(exp_day))
    asset_type = {"C":"CALL", "P":"PUT", "S":"STOCK", "E":"STOCK"}.get(asset_char)
    return underlying, exp, asset_type, float(strike_str)


def convert_position_from_td(tdp):
    p = PyJSON(tdp)
    _, p.expiration, _, p.strike = decode_tda_symbol(p.instrument.symbol)
    p.quantity = p.longQuantity - p.shortQuantity
    p.is_call = (p.instrument.putCall == "CALL")
    p.is_put = (p.instrument.putCall == "PUT")
    return p


def convert_option_from_td(tdo):
    p = PyJSON(tdo)
    return p


def convert_order_from_td(tdo):
    p = PyJSON(tdo)
    return p


def convert_chain_from_td(tdo):
    p = PyJSON(tdo)
    return p


def convert_contract_from_td(tdo):
    p = PyJSON(tdo)
    return p


def group_positions_by_underlying(data):
    posns = {}
    for d in data:
        if d.instrument.underlyingSymbol not in posns:
            posns[d.instrument.underlyingSymbol] = []
        posns[d.instrument.underlyingSymbol].append(d)
    return posns


def identify_synthetic_trade(p):
    # Synths are 3-legged
    if len(p) != 3:
        return None

    # Identify the short and two long legs
    spread_short = long_leg_1 = long_leg_2 = None
    single = spread_long = None
    exp = qty = None  
    for leg in p:
        # Validate all legs have the same expiration and quantity
        if qty is None:
            qty = abs(leg.quantity)
            exp = leg.expiration
        elif qty != abs(leg.quantity) or exp != leg.expiration:
            return None

        if leg.quantity < 0.0:
            spread_short = leg
        elif long_leg_1:
            long_leg_2 = leg
        else:
            long_leg_1 = leg

    # Identify the spread and single
    if long_leg_1.instrument.putCall == spread_short.instrument.putCall:
        spread_long = long_leg_1
        single = long_leg_2
    elif long_leg_2.instrument.putCall == spread_short.instrument.putCall:
        spread_long = long_leg_2
        single = long_leg_1
    else:
        # Invalid spread
        return None

    # Validate the strikes
    if single.is_call and not (single.strike >= spread_short.strike > spread_long.strike):
        return None
    if single.is_put and not (single.strike <= spread_short.strike < spread_long.strike):
        return None

    # Asset types right?
    if single.is_call:
        if not (spread_long.is_put and spread_short.is_put):
            return None
    elif single.is_put:
        if not (spread_long.is_call and spread_short.is_call):
            return None
    else:
        return None

    j = {
        "single": single,
        "spread_long": spread_long,
        "spread_short": spread_short
    }
    return PyJSON(j)


def is_option_order_for_symbol(underlying, order):
    # Already closed?
    if order.closeTime:
        return False

    # Have legs?
    if not order.orderLegCollection:
        return False

    for order_leg in order.orderLegCollection:
        if order_leg.orderLegType == "OPTION":
            leg_underlying, _, _, _ = decode_tda_symbol(order_leg.symbol)
            if leg_underlying == underlying:
                return True
    return False


def find_contract_closest_to_50_delta(broker, current_leg):
     # Get the contract closest to 0.5 delta of the same type
    # contract_type='ALL', strike_count=20, from_date=None, to_date=None
    best_contract = None

    current_underlying = current_leg.instrument.underlyingSymbol
    exp_date = current_leg.expiration.format('YYYY-MM-DD')
    chains = broker.option_chains(symbol=current_underlying, contract_type=current_leg.instrument.putCall, 
                                  strike_count=20, from_date=exp_date, to_date=exp_date)
    if not chains:
        print(f"No contracts for {current_underlying} to roll {current_leg.instrument.symbol}.")
        return None

    optionDateMap = None
    if current_leg.is_put:
        optionDateMap = chains["putExpDateMap"]
    elif current_leg.is_call:
        optionDateMap = chains["callExpDateMap"]
    
    # Manage this iteration using the raw TDA return (PyJSON has not items() method)
    contracts = []
    for contract_exp_date, contract_strike_chains in optionDateMap.items():
        for contract_strike, contracts_for_strike in contract_strike_chains.items():
            tmp = [PyJSON(x) for x in contracts_for_strike]
            contracts.extend(tmp)
    contracts = sorted(contracts, key=lambda c: abs(0.5 - abs(c.delta)))
    best_contract = contracts[0]
    if best_contract.openInterest < 5:
        print(f"Warning: Low open interest in {best_contract.symbol}")

    return best_contract


def is_order_open(orders, underlying):
    for x in orders:
        if is_option_order_for_symbol(underlying, x):
            return True
    return False


def place_roll_order(price, quantity, new_symbol, old_symbol):
    order = {
        "orderStrategyType": "SINGLE",
        "orderType": "LIMIT",
        "session": "NORMAL",
        "duration": "DAY",
        "price": f"{price}",
        "complexOrderStrategyType": "CUSTOM",
        "orderLegCollection": [
            {
            "instrument": {
                "assetType": "OPTION",
                "symbol": f"{new_symbol}"
            },
            "instruction": "BUY_TO_OPEN",
            "quantity": quantity
            },
            {
            "instrument": {
                "assetType": "OPTION",
                "symbol": f"{old_symbol}"
            },
            "instruction": "SELL_TO_CLOSE",
            "quantity": quantity
            }
        ]
    }
    # broker.place_custom_order(order)
    print(f"Entered order to roll:\n{order}\n")


def place_close_order(leg):
    order = {
        "orderStrategyType": "SINGLE",
        "orderType": "LIMIT",
        "session": "NORMAL",
        "duration": "DAY",
        "price": f"{leg.marketValue / (100.0 * leg.shortQuantity)}",
        "orderStrategy": "SINGLE",
        "orderLegCollection": [
            {
                "instruction": "BUY_TO_OPEN",
                "quantity": leg.shortQuantity,
                "instrument": {
                    "assetType": "OPTION",
                    "symbol": f"{leg.instrument.symbol}"
                }
            }
        ]
    }
    # broker.place_custom_order(order)
    print(f"Entered order to buy-to-close:\n{order}\n")


def roll_to_fifty_delta(broker, orders, current_leg):
    # If there ANY orders for the underlying, return taking no action.
    current_underlying = current_leg.instrument.underlyingSymbol
    if is_order_open(orders, current_underlying):
        print(f"Skipping: There are open orders on {current_underlying}")

    best_contract = find_contract_closest_to_50_delta(broker, current_leg)
    price = best_contract.ask * 100 * current_leg.longQuantity
    old_price = current_leg.marketValue
    if price >= old_price:
        print(f"Skipping: Roll-to {best_contract.symbol} lower value ${price} than {current_leg.instrument.symbol} market value ${old_price}")
        return
    
    place_roll_order(old_price - price, current_leg.longQuantity, current_leg.instrument.symbol, best_contract.symbol)
    return
    

def roll_synthetics(min_delta=0.8, short_leg_close_ask=0.05):
    # Verify environment variables are set
    broker = connect_to_tda()
    orders = broker.orders()
    orders = [convert_order_from_td(order) for order in orders]
    tda_positions = broker.positions()
    positions = [convert_position_from_td(p) for p in tda_positions]
    
    synths = []
    positions = group_positions_by_underlying(positions)
    for legs in positions.values():
        trade = identify_synthetic_trade(legs)
        if trade:
            synths.append(trade)
    
    if not synths:
        print("No synthetics to roll.")
        return

    for s in synths:
        # Fetch the single leg and get the greek.delta
        tda_option_symbol = s.single.instrument.symbol
        
        # The single leg might actually have been bought over multiple rounds.
        rolling_legs = broker.quote(tda_option_symbol)
        for tda_symbol, tda_option in rolling_legs.items():

            # Check for delta roll
            contract = convert_contract_from_td(tda_option)
            if s.single.is_call and contract.delta >= min_delta:
                print(f'Ready to roll CALL {tda_symbol} with delta {contract.delta}')
                roll_to_fifty_delta(broker, orders, s.single)
            elif s.single.is_put and contract.delta <= -min_delta:
                print(f'Ready to roll PUT {tda_symbol} with delta {contract.delta}')
                roll_to_fifty_delta(broker, orders, s.single)

            # TODO: TEST TEST TEST
            # Check for early close on the short leg
            if 0 < s.spread_short.marketValue <= short_leg_close_ask*100*s.spread_short.quantity:
                print(f"Attempt to close this short leg {s.spread_short.instrument.symbol}")
                if is_option_order_for_symbol(s.instrument.underlying):
                    print(f"Skipping: Order open on {s.instrument.underlying}")
                    continue
                place_close_order(s.spread_short)
