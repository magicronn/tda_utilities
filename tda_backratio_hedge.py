import json
import arrow
import td_ameritrade_api as td
from .tda_connect import connect_to_tda
from .pyjson import PyJSON

def manage_backratios(trigger_pct=2.0, reinvest=True):

    # Verify environment variables are set
    broker = connect_to_tda()
    # orders = broker.orders()
    # orders = [convert_order_from_td(order) for order in orders]
    # tda_positions = broker.positions()
    # positions = [convert_position_from_td(p) for p in tda_positions]
    
    # synths = []
    # positions = group_positions_by_underlying(positions)
    # for legs in positions.values():
    #     trade = identify_synthetic_trade(legs)
    #     if trade:
    #         synths.append(trade)
    
    # if not synths:
    #     print("No synthetics to roll.")
    #     return

    # for s in synths:
    #     # Fetch the single leg and get the greek.delta
    #     tda_option_symbol = s.single.instrument.symbol
        
    #     # The single leg might actually have been bought over multiple rounds.
    #     rolling_legs = broker.quote(tda_option_symbol)
    #     for tda_symbol, tda_option in rolling_legs.items():

    #         # Check for delta roll
    #         contract = convert_contract_from_td(tda_option)
    #         if s.single.is_call and contract.delta >= min_delta:
    #             print(f'Ready to roll CALL {tda_symbol} with delta {contract.delta}')
    #             roll_to_fifty_delta(broker, orders, s.single)
    #         elif s.single.is_put and contract.delta <= -min_delta:
    #             print(f'Ready to roll PUT {tda_symbol} with delta {contract.delta}')
    #             roll_to_fifty_delta(broker, orders, s.single)

    #         # TODO: TEST TEST TEST
    #         # Check for early close on the short leg
    #         if 0 < s.spread_short.marketValue <= short_leg_close_ask*100*s.spread_short.quantity:
    #             print(f"Attempt to close this short leg {s.spread_short.instrument.symbol}")
    #             if is_option_order_for_symbol(s.instrument.underlying):
    #                 print(f"Skipping: Order open on {s.instrument.underlying}")
    #                 continue
    #             place_close_order(s.spread_short)
