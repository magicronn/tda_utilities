'''Doc string TBD...'''


from os import path, rename
import arrow
from dotenv import load_dotenv


client_id = input("Enter your TDA Oauth consumer ID, e.g. ABCDEFGHIJKLM@AMER.OAUTH: ")
account_id = input("Enter the TDA account number to use: ")
refresh_token = input("Enter your TDA refresh token: ")

# If a .env exists, back it up first.
if path.exists('.env'):
    # Rename it with time stamp 
    bkup_name = f".env_bkup_{arrow.now().timestamp}"
    rename('.env', bkup_name)
    print(f'Existing .env file moved to {bkup_name}')

with open('.env', 'w+') as f:
    f.writelines([
        f"client_id={client_id}\n",
        f"account_id={account_id}\n",
        f"refresh_token={refresh_token}\n"
    ])
print('Configuration stored in .env. It contains secrets. Do not share or check this file into a repo.')
