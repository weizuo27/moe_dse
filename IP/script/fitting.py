import argparse
import numpy as np
import math
from sklearn.linear_model import LinearRegression
import pickle
import os
from pareto_front import is_pareto_efficient
def fitting_model():
    Tm_Tn_list = []
    Lat_list = []
    dsp_list = []
    lut_list = []
    bram_list = []
    ff_list = []
    with open(f"{build_dir}/ip_csv.log", "r") as fr:
        for line in fr:
            M, N, K, Tm, Tn, Tk, Lat, dsp, lut, bram, ff, dsp_pct, lut_pct , bram_pct, ff_pct= list(map(int, line.split(",")))
            if(Tm == 8 and Tn == 128 and Tk == 256):
                print("found", Lat)
            Lat_per_tile = Lat / math.ceil(M/Tm) /math.ceil(N/Tn)
            Tm_Tn_list.append((Tm, Tn))
            Lat_list.append(Lat_per_tile)
            dsp_list.append(dsp_pct)
            lut_list.append(lut_pct)
            bram_list.append(bram_pct)
            ff_list.append(ff_pct)

    Tm_Tn_array = np.array(Tm_Tn_list)
    Lat_array = np.array(Lat_list)
    dsp_array = np.array(dsp_list)
    lut_array = np.array(lut_list)
    ff_array = np.array(ff_list)
    bram_array =np.array(bram_list)

    reg_lat = LinearRegression().fit(Tm_Tn_array, Lat_array)
    reg_dsp = LinearRegression().fit(Tm_Tn_array, dsp_array)
    reg_lut = LinearRegression().fit(Tm_Tn_array, lut_array)
    reg_bram = LinearRegression().fit(Tm_Tn_array, bram_array)
    reg_ff = LinearRegression().fit(Tm_Tn_array, ff_array)

    print("lat_score", reg_lat.score(Tm_Tn_array, Lat_array))
    print("dsp_score", reg_dsp.score(Tm_Tn_array, dsp_array))
    print("lut_score", reg_lut.score(Tm_Tn_array, lut_array))
    print("ff score", reg_ff.score(Tm_Tn_array, ff_array))
    print("bram score", reg_bram.score(Tm_Tn_array, bram_array))
    return reg_lat, reg_dsp, reg_lut, reg_ff, reg_bram

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-build_dir', type=str, required=True) #The directory in which HLS IPs are 
    args = parser.parse_args()
    build_dir = args.build_dir

    if not (os.path.isfile(f"{build_dir}/reg_lat.sav") and 
            os.path.isfile(f"{build_dir}/reg_dsp.sav") and 
            os.path.isfile(f"{build_dir}/reg_ff.sav") and 
            os.path.isfile(f"{build_dir}/reg_bram.sav") and 
            os.path.isfile(f"{build_dir}/reg_lut.sav")):
        print("files not exist")
        reg_lat, reg_dsp, reg_lut, reg_ff, reg_bram = fitting_model()
        pickle.dump(reg_lat, open(f"{build_dir}/reg_lat.sav", 'wb'))
        pickle.dump(reg_lut, open(f"{build_dir}/reg_lut.sav", 'wb'))
        pickle.dump(reg_dsp, open(f"{build_dir}/reg_dsp.sav", 'wb'))
        pickle.dump(reg_bram, open(f"{build_dir}/reg_bram.sav", 'wb'))
        pickle.dump(reg_ff, open(f"{build_dir}/reg_ff.sav", 'wb'))
    else:
        print("files exist")
        reg_lat = pickle.load(open(f"{build_dir}/reg_lat.sav", 'rb'))
        reg_dsp = pickle.load(open(f"{build_dir}/reg_dsp.sav", 'rb'))
        reg_lut = pickle.load(open(f"{build_dir}/reg_lut.sav", 'rb'))


    costs_list = []
    N_const = 3072
    K_const = 768
    Tk = 256 #make Tk be dividable by both N_const and K_const

    N = 3072
    K = 3072
    M = 450

    for Tm in range(8, 512, 8):
        for Tn in range(128, 3072, 128):
            Lat_iter = ((reg_lat.predict(np.array([[Tm, Tn]]))/math.ceil(K/Tk))[0])
            dsp_pct = int(math.ceil(reg_dsp.predict(np.array([[Tm, Tn]]))[0]))
            lut_pct = int(math.ceil(reg_lut.predict(np.array([[Tm, Tn]]))[0]))
            Lat_M_iter = Lat_iter * (math.ceil(N_const/Tn) * math.ceil(K_const/Tk) + math.ceil(K_const/Tn) * math.ceil(N_const/Tk))
            costs_list.append([M, N, K, Tm, Tn, Tk, -Tm, Lat_M_iter, dsp_pct, lut_pct])

    print("len(costs_list)=", len(costs_list))
    costs = np.array(costs_list)

    pareto_mask = is_pareto_efficient(costs[:,6:], return_mask = True)
    pareto_cost_array = costs[pareto_mask]
    print('shape(pareto_cost_array)=', pareto_cost_array.shape)
    mask = is_pareto_efficient(pareto_cost_array[:,6:], margin = 0.01)
    approx_pareto_array = pareto_cost_array[mask].tolist()
    print("len(approx_pareto_array)=", len(approx_pareto_array))

    sorted_approx_pareto = (sorted(approx_pareto_array, key=lambda x: math.ceil(x[7]/x[3])))
    
    idx = 0
    with open(f"{build_dir}/ip_candidates_new.log", mode ='w') as f:
        for ip in sorted_approx_pareto:
            ip = [idx] + ip
            idx +=1
            out = " ".join(str(i) for i in ip)
            f.write(out+"\n")

    #print("reg_lat", reg_lat.coef_, reg_lat.intercept_)
    #print("reg_dsp", reg_dsp.coef_, reg_dsp.intercept_)
    #print("reg_lut", reg_lut.coef_, reg_lut.intercept_)

    #print("lat_score", reg_lat.score(Tm_Tn_array, Lat_array))
    #print("dsp_score", reg_dsp.score(Tm_Tn_array, dsp_array))
    #print("lut_score", reg_lut.score(Tm_Tn_array, lut_array))

    #print(reg_lat.predict(np.array([[1, 1536]])), reg_dsp.predict(np.array([[1, 1536]])), reg_lut.predict(np.array([[1, 1536]])))
    #print(reg_lat.predict(np.array([[32, 1536]])), reg_dsp.predict(np.array([[32, 1536]])), reg_lut.predict(np.array([[32, 1536]])))
    #print(reg_lat.predict(np.array([[64, 1536]])), reg_dsp.predict(np.array([[64, 1536]])), reg_lut.predict(np.array([[64, 1536]])))
    #print(reg_lat.predict(np.array([[128, 1536]])), reg_dsp.predict(np.array([[128, 1536]])), reg_lut.predict(np.array([[128, 1536]])))

