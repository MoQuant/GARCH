# Financial Modeling Prep's Historical Price API
def historicalData(ticker):
    key = 'apikey=' # ENTER FMP KEY HERE
    url = f'https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?{key}'
    return url

import asyncio
import aiohttp
import websockets
import json
import numpy as np
import pandas as pd
import ctypes
from scipy.optimize import minimize

# Initialize the Geometric Browninan Motion function from C and add argument and result types
cd = ctypes.c_double
ci = ctypes.c_int

lib = ctypes.CDLL("./gbm.so")
lib.GBM.argtypes = (cd, cd, cd, cd, ci, ci)
lib.GBM.restype = cd

# Conducts optimization to generate the GARCH parameters
def Optimization(returns):
    # Maximize log-likelihood
    def Objective(x, r):
        total = 0
        o2 = r[0]**2
        for t in range(1, len(r)):
            o2 = x[0] + x[1]*(r[t-1]**2) + x[2]*o2
            total += np.log(o2) + (r[t-1]**2)/o2
        total *= 0.5
        return -total
    x = 0.01*np.ones(3)
    # Use a negative sign so the minimization converts to a maximization
    res = minimize(Objective, x, args=(returns,), method='SLSQP', bounds=[(0.01, 0.5), (0.01, 1), (0.01, 1)], constraints=[{'type':'eq','fun':lambda x: 1.0 - sum(x)}])
    return res.x


class Server:

    # Set the host and port of the server
    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port

    # Start the WebSocket Server
    def ignite(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(websockets.serve(self.server, self.host, self.port))
        loop.run_forever()

    # WebSocket Server which connects to React
    async def server(self, ws, path):
        print("Connected to Client........")
        async with aiohttp.ClientSession() as session:
            while True:
                # Fetch the parameters from the client
                msg = await ws.recv()

                # Parse the parameters and make sure they are integers apart from the ticker
                ticker, FN, Paths, Steps, T = json.loads(msg)
                FN = int(FN)
                Paths = int(Paths)
                Steps = int(Steps)
                T = int(T)/365.0

                # Fetch the historical price data from FMP's API
                async with session.get(historicalData(ticker)) as response:
                    resp = await response.text()
                    resp = json.loads(resp)

                    # Calculate the rate of return for the imported stock
                    close = pd.DataFrame(resp['historical'])['adjClose'][::-1].values
                    xror = close[1:]/close[:-1] - 1.0

                    VOLATILITY = []
                    GBMPRICE = []

                    # Cut returns into a rolling window xror to calculate the GARCH weights for each snapshot of returns
                    for k in range(FN, len(xror)):
                        ror = xror[k-FN:k]

                        # Garch Parameters
                        a0, a1, B = Optimization(ror)

                        # GBM Parameters
                        S0 = close[-1]
                        drift = np.mean(ror)
                        dt = T / Steps

                        vol = np.zeros(FN)
                        rtn = np.zeros(FN)

                        # Initial Variance and Return from Historical Data
                        vol[0] = np.var(ror)
                        rtn[0] = ror[-1]

                        ror = ror.tolist()

                        # Run the GARCH model on volatilty and append the last element of vol to the VOLATILITY list
                        for t in range(1, FN):
                            vol[t] = a0 + a1*(rtn[t-1]**2) + B*vol[t-1]

                        VOLATILITY.append(float(np.sqrt(vol[-1])))

                        # View GARCH parameters
                        print(a0, a1, B)

                        # Conduct a Geometric Brownian Motion simulation with the latest GARCH volatility
                        tS = lib.GBM(S0, drift, dt, VOLATILITY[-1], Paths, Steps)
                        GBMPRICE.append(tS)

                        # Send the client a message with the GARCH and GBM charts
                        msg = {'type':'message','payload':f'Days Left: {len(xror) - k}'}
                        await ws.send(json.dumps(msg))
                    
                        VX, SX = VOLATILITY[:k], GBMPRICE[:k]
                        x = list(range(len(VX)))
                        msg = {'type':'graph','payload':{'x':x,'y':VX,'x2':x,'y2':SX, 'price':float(close[-1])}}
                        await ws.send(json.dumps(msg))

print("Server Booted......")
Server().ignite()
