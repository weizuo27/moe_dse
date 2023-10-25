import pickle
import argparse
import numpy as np
import math
from utils import generate_expert_list, generate_IP_list, generate_selected_ips, generate_modeling_latency

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-ilp_sol', type=str, required=True)
    parser.add_argument('-ip_file_name', type=str, required=True)
    parser.add_argument('-build_dir', type=str, required=True)

    args = parser.parse_args()
    build_dir = args.build_dir

    selected_ips = dict()

    generate_selected_ips(args.ilp_sol, args.ip_file_name, selected_ips, None)

    ip_candidates = generate_IP_list(args.ip_file_name)

    modeling_lat = generate_modeling_latency(args.ilp_sol)

    reg_lat = pickle.load(open(f"{build_dir}/reg_lat.sav", 'rb'))
    reg_dsp = pickle.load(open(f"{build_dir}/reg_dsp.sav", 'rb'))
    reg_lut = pickle.load(open(f"{build_dir}/reg_lut.sav", 'rb'))
    reg_ff = pickle.load(open(f"{build_dir}/reg_ff.sav", 'rb'))
    reg_bram = pickle.load(open(f"{build_dir}/reg_bram.sav", 'rb'))

    lut = dsp = ff = bram = 0
    for i, j in selected_ips.items():
        Tm, Tn, Tk = int(ip_candidates[i].Tm), int(ip_candidates[i].Tn), int(ip_candidates[i].Tk)

        print("i, j,Tm, Tn, Tk, lut, dsp, ff, bram", i, j,  Tm, Tn, Tk,
        math.ceil(reg_lut.predict(np.array([[Tm, Tn]]))[0]),
        math.ceil(reg_dsp.predict(np.array([[Tm, Tn]]))[0]),
        math.ceil(reg_ff.predict(np.array([[Tm, Tn]]))[0]),
        math.ceil(reg_bram.predict(np.array([[Tm, Tn]]))[0]))

        lut += math.ceil(reg_lut.predict(np.array([[Tm, Tn]]))[0]) * j
        dsp += math.ceil(reg_dsp.predict(np.array([[Tm, Tn]]))[0]) * j
        ff += math.ceil(reg_ff.predict(np.array([[Tm, Tn]]))[0]) * j
        bram += math.ceil(reg_bram.predict(np.array([[Tm, Tn]]))[0]) * j
    print("modeling_lat", modeling_lat)
    print("bram, dsp, ff, lut", round(bram), round(dsp), round(ff), round(lut))
