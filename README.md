# tda_utilities

This package provides simple CLI utilities for option strategies on TD Ameritrade. 
The default action is to look at all open option positions and, if there are no outstanding orders against them,
1. reduce risk by closing short option positions that are cheap
2. take credit by rolling long option positions back to ATM (delta 0.5).


## Installation

Have Python 3 installed because there is no Python 2.
1. Clone the repo: `git clone http://github.com/magicronn/tda_utilities`
2. Install requirements: `pip install -r requirements.txt`
3. Get your account ID and refresh token from 
[TD Ameritrade - Developer Getting Started](https://developer.tdameritrade.com/content/getting-started)
4. Create your .env file and give your full oauth ID, TDA account number, and refresh token: `python config.py`
5. Run `python tda.py`
