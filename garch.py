# Historical Data Fetcher
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

# Declare GBM function from C and assign datatypes to arguments and result
cd = ctypes.c_double
ci = ctypes.c_int

lib = ctypes.CDLL("./gbm.so")
lib.GBM.argtypes = (cd, cd, cd, cd, ci, ci)
lib.GBM.restype = cd

# Optimize the GARCH model for each iteration of returns
def Optimization(returns):
    # Objective maximizing the GARCH log-likelihood function with the negative sign for optimizer
    def Objective(x, r):
        total = 0
        o2 = r[0]**2
        for t in range(1, len(r)):
            o2 = x[0] + x[1]*(r[t-1]**2) + x[2]*o2
            total += np.log(o2) + (r[t-1]**2)/o2
        total *= 0.5
        return -total
    x = [0.1, 0.1, 0.1]

    # It is really maximizing with the negative sign
    res = minimize(Objective, x, args=(returns,))
    return res.x

# Server class which loads data and generates a response to send to the client when parameters are received
class Server:

    # Initialize the host and port
    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port

    # Start the websocket server
    def ignite(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(websockets.serve(self.server, self.host, self.port))
        loop.run_forever()

    # Websocket server
    async def server(self, ws, path):
        print("Connected to Client........")
        async with aiohttp.ClientSession() as session:
            while True:
                # Fetches the parameters from the client
                msg = await ws.recv()

                # Parses the inputs using JSON
                ticker, FN, Paths, Steps, T = json.loads(msg)

                # Makes sure integers are passed through
                FN = int(FN)
                Paths = int(Paths)
                Steps = int(Steps)
                T = int(T)/365.0

                # Fetches the historical data
                async with session.get(historicalData(ticker)) as response:
                    resp = await response.text()
                    resp = json.loads(resp)

                    # Computes the rate of returns based on imported close prices
                    close = pd.DataFrame(resp['historical'])['adjClose'][::-1].values
                    ror = close[1:]/close[:-1] - 1.0

                    # Optimize the GARCH model parameters
                    a0, a1, B = Optimization(ror)

                    # Generate inputs to the Geometric Brownian Motion simulation
                    S0 = close[-1]
                    drift = np.mean(ror)
                    dt = T / Steps

                    # Initialize volatilty and return arrays with the initial variance and latest return
                    vol = np.zeros(FN)
                    rtn = np.zeros(FN)

                    vol[0] = np.var(ror)
                    rtn[0] = ror[-1]

                    ror = ror.tolist()
                    for t in range(1, FN):
                        # Garch model computation
                        vol[t] = a0 + a1*(rtn[t-1]**2) + B*vol[t-1]

                        # GBM model computation
                        S1 = lib.GBM(S0, drift, dt, vol[t], Paths, Steps)

                        # Rate of Return of simulation
                        rtn[t] = (S1/S0) - 1.0

                        # Erase first element of rate of returns list
                        del ror[0]

                        # Add latest return to rate of returns list
                        ror.append(rtn[t])

                        # Optimize the new GARCH parameters
                        a0, a1, B = Optimization(ror)

                        # Set initial stock price to simulated stock price 
                        S0 = S1

                        # Send server messages on how much longer the simulation will last
                        left = FN - t
                        msg = {'type':'message','payload':f'Days Left: {left}'}
                        await ws.send(json.dumps(msg))

                    
                    msg = {'type':'message','payload':'Waiting for Forecast'}
                    await ws.send(json.dumps(msg))
                    plot = np.sqrt(vol).tolist()
                    
                    # Send plotting data over server to be plotted on Plotly.js
                    x = list(range(len(plot)))
                    msg = {'type':'graph','payload':{'x':x,'y':plot}}
                    await ws.send(json.dumps(msg))

print("Server Booted......")
Server().ignite()
