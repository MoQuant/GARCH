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

cd = ctypes.c_double
ci = ctypes.c_int

lib = ctypes.CDLL("./gbm.so")
lib.GBM.argtypes = (cd, cd, cd, cd, ci, ci)
lib.GBM.restype = cd

def Optimization(returns):
    def Objective(x, r):
        total = 0
        o2 = r[0]**2
        for t in range(1, len(r)):
            o2 = x[0] + x[1]*(r[t-1]**2) + x[2]*o2
            total += np.log(o2) + (r[t-1]**2)/o2
        total *= 0.5
        return -total
    x = 0.01*np.ones(3)
    res = minimize(Objective, x, args=(returns,), method='SLSQP', bounds=[(0.01, 0.5), (0.01, 1), (0.01, 1)], constraints=[{'type':'eq','fun':lambda x: 1.0 - sum(x)}])
    return res.x


class Server:

    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port

    def ignite(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(websockets.serve(self.server, self.host, self.port))
        loop.run_forever()

    async def server(self, ws, path):
        print("Connected to Client........")
        async with aiohttp.ClientSession() as session:
            while True:
                msg = await ws.recv()
                ticker, FN, Paths, Steps, T = json.loads(msg)
                FN = int(FN)
                Paths = int(Paths)
                Steps = int(Steps)
                T = int(T)/365.0
                async with session.get(historicalData(ticker)) as response:
                    resp = await response.text()
                    resp = json.loads(resp)
                    close = pd.DataFrame(resp['historical'])['adjClose'][::-1].values
                    xror = close[1:]/close[:-1] - 1.0

                    VOLATILITY = []
                    GBMPRICE = []

                    for k in range(FN, len(xror)):
                        ror = xror[k-FN:k]
                        a0, a1, B = Optimization(ror)
                        
                        S0 = close[-1]
                        drift = np.mean(ror)
                        dt = T / Steps

                        vol = np.zeros(FN)
                        rtn = np.zeros(FN)

                        vol[0] = np.var(ror)
                        rtn[0] = ror[-1]

                        ror = ror.tolist()

                        for t in range(1, FN):
                            vol[t] = a0 + a1*(rtn[t-1]**2) + B*vol[t-1]

                        VOLATILITY.append(float(np.sqrt(vol[-1])))
                        print(a0, a1, B)
                        tS = lib.GBM(S0, drift, dt, VOLATILITY[-1], Paths, Steps)
                        GBMPRICE.append(tS)
                        
                        msg = {'type':'message','payload':f'Days Left: {len(xror) - k}'}
                        await ws.send(json.dumps(msg))
                    
                        VX, SX = VOLATILITY[:k], GBMPRICE[:k]
                        x = list(range(len(VX)))
                        msg = {'type':'graph','payload':{'x':x,'y':VX,'x2':x,'y2':SX, 'price':float(close[-1])}}
                        await ws.send(json.dumps(msg))

print("Server Booted......")
Server().ignite()
