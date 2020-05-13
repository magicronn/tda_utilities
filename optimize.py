import json
import arrow
import td_ameritrade_api as td
from .tda_connect import *
from .pyjson import PyJSON


def is_option_order_for_symbol(underlying, order):
    # Still in queue?
    if order.status != "QUEUED":
        return False

    # Have legs?
    if not order.orderLegCollection:
        return False

    for x in order.orderLegCollection:
        if x["orderLegType"] == "OPTION":
            leg_underlying, _, _, _ = decode_tda_symbol(x["instrument"]["symbol"])
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
        "price": price,
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
    # TODO: marketValue is midpoint of bid-ask spread. Should fetch the current contract for this leg and use that bid.
    # Acceptable for now since credit will be better than using that bid.
    # TODO: Add commission to final price
    old_price = current_leg.marketValue
    if price >= old_price:
        print(f"Skipping: Roll-to {best_contract.symbol} lower value ${price} than {current_leg.instrument.symbol} market value ${old_price}")
        return
    
    # Price should be negative - this order should generate a credit
    place_roll_order(price - old_price, current_leg.longQuantity, current_leg.instrument.symbol, best_contract.symbol)
    return
    

def optimize_all_positions(min_delta=0.8, short_close_ask=0.05):
    '''
    optimize_all_positions iterates over all option and equity positions by underlying and 
    attempts to reduce risk and extract value. Currently this is limited to rolling longs that have large delta
    and closing shorts that have small asks. Later work may include rolling positions to the next series
    for additional time/value.
    :param legs: Array of contracts with quantities, etc. JSON as defined by TDA.
    :type legs: object
    :param min_delta: Minimum delta to roll long legs down to 0.5 delta, taking profits.
    :type min_delta: float
    :param short_close_ask: Maximumn price to pay to close a short leg early, minimizing risk.
    :type short_close_ask: float 
    '''
    broker = connect_to_tda()
    orders = broker.orders()
    orders = [convert_to_pyjson(order) for order in orders]
    positions = broker.positions()
    positions = [convert_position_from_td(p) for p in positions]
    positions = group_positions_by_underlying(positions)
    for legs in positions.values():
        close_cheap_shorts(broker, orders, legs, short_close_ask)
        roll_position_longs(broker, orders, legs, min_delta)


def roll_position_longs(broker, orders, legs, min_delta=0.8):
    '''
    roll_long_legs identifies unmatched legs in all trades and attempts to roll them if their delta
    is above the given minimum.
    :param broker: TDA instance
    :param orders: open orders from TDA (to prevent redundant calls)
    :param legs: Array of contracts with quantities, etc. JSON as defined by TDA.
    :type legs: object
    :param min_delta: Minimum delta to roll long legs down to 0.5 delta, taking profits.
    :type min_delta: float
    :param short_close_ask: Maximumn price to pay to close a short leg early, minimizing risk.
    :type short_close_ask: float 
    '''
    for leg in legs:
        # Validate all legs have the same expiration and quantity
        if leg.quantity > 0:
            tda_option_symbol = leg.instrument.symbol
        
            # The single leg might actually have been bought over multiple rounds.
            rolling_legs = broker.quote(tda_option_symbol)
            for tda_symbol, tda_option in rolling_legs.items():

                # Check for delta for potential roll
                contract = convert_to_pyjson(tda_option)
                if leg.is_call and contract.delta >= min_delta:
                    print(f'Ready to roll CALL {tda_symbol} with delta {contract.delta}')
                    roll_to_fifty_delta(broker, orders, leg)
                elif leg.is_put and contract.delta <= -min_delta:
                    print(f'Ready to roll PUT {tda_symbol} with delta {contract.delta}')
                    roll_to_fifty_delta(broker, orders, leg)


def close_cheap_shorts(broker, orders, legs, short_close_ask):
    '''
    close_position_shorts closes any leg with single contract value less than the given ask. Won't 
    do anything if there are existing orders for the underlying.
    :param broker: TDA instance
    :param orders: open orders from TDA (to prevent redundant calls)
    :param legs: Array of contracts with quantities, etc. JSON as defined by TDA.
    :type legs: object
    :param short_close_ask: Maximumn price to pay to close a short leg early, minimizing risk.
    :type short_close_ask: float 
    '''

    for leg in legs:
        # Validate all legs have the same expiration and quantity
        if 0 < leg.marketValue <= short_close_ask*100*leg.shortQuantity:
            print(f"Attempt to close this short leg: {leg.instrument.symbol}")
            if not is_option_order_for_symbol(leg.underlying):
                place_close_order(leg)
            else: 
                print(f"Skipping: Short close order due to open order on {leg.underlying} options")
