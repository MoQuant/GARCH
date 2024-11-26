#include <math.h>
#include <time.h>
#include <stdlib.h>
#include <stdio.h>

double dWT(){
    int num = 3;
    double y = (rand() % (2*num + 1)) - num;
    return y/100.0;
}

double GBM(double S, double drift, double dt, double vol, int Paths, int Steps){
    srand(time(NULL));
    double result = 0;
    for(int p = 0; p < Paths; ++p){
        double S0 = S;
        for(int s = 0; s < Steps; ++s){
            S0 += drift*S0*dt + sqrt(vol)*S0*dWT();
        }
        result += S0;
    }
    result = result / (double) Paths;
    return result;
}