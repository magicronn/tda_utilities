import os
import arrow
from dotenv import load_dotenv
from .pyjson import PyJSON
import td_ameritrade_api as td


def connect_to_tda():
    load_dotenv(verbose=True)   
    refresh_token = os.environ.get('refresh_token', None)
    client_id = os.environ.get('consumer_id', None)
    account_id = os.environ.get('account_id', None)
    if not (refresh_token and client_id and account_id): 
        raise Exception("Environment variables not set")
    client = td.client(refresh_token, client_id, account_id)
    return client


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
    p = convert_to_pyjson(tdp)

    # TODO: If this is an option...
    _, p.expiration, _, p.strike = decode_tda_symbol(p.instrument.symbol)
    p.quantity = p.longQuantity - p.shortQuantity
    p.is_call = (p.instrument.putCall == "CALL")
    p.is_put = (p.instrument.putCall == "PUT")

    # TODO: Else it is a stock/ETF
    return p


def convert_to_pyjson(tdo):
    p = PyJSON(tdo)
    return p


def group_positions_by_underlying(data):
    posns = {}
    for d in data:
        if d.instrument.underlyingSymbol not in posns:
            posns[d.instrument.underlyingSymbol] = []
        posns[d.instrument.underlyingSymbol].append(d)
    return posns
