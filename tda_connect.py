import os
from dotenv import load_dotenv

def connect_to_tda():
    load_dotenv(verbose=True)   
    refresh_token = os.environ.get('refresh_token', None)
    client_id = os.environ.get('consumer_id', None)
    account_id = os.environ.get('account_id', None)
    if not (refresh_token and client_id and account_id): 
        raise Exception("Environment variables not set")
    client = td.client(refresh_token, client_id, account_id)
    return client
