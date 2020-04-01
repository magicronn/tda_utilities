# tda_utilities

These files all provide simple CLI to help with individual strategies. 
* config: cli to populate a .env for connecting to your TDA account.
* tda_delta_roller: manages basic synthetics, long and short
* tda_backratio_hedge: manages a backratio hedge against a long-term holding

## Installation

Have Python 3 because there is no Python 2.
1. Clone the repo: `git clone http://github.com/magicronn/tda_utilities`
2. Install requirements: `pip install -r requirements.txt`
3. Get your account ID and refresh token from 
[TD Ameritrade - Developer Getting Started](https://developer.tdameritrade.com/content/getting-started)
4. Create your .env file and give your full oauth ID, secret, and refresh token: `python config.py`
5. Run the utility of your choice. See the individual documentation for details.
