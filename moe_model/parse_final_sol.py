import argparse
import subprocess
from multiprocessing import Process, Semaphore
import os
import re
from utils import generate_expert_list, generate_IP_list, generate_selected_ips, generate_modeling_latency

import subprocess

def hls_fun(proc_num, build_dir, root_dir, M, N, K, Tm, Tn, Tk, sema):
    sema.acquire()
    print(f"Process {proc_num}: M, N, K = {M}, {N}, {K}; Tm, Tn, Tk = {Tm}, {Tn}, {Tk}\n")
    hls_proj_dir = f"matmul_hls_tile_M{M}_N{N}_K{K}_Tm{Tm}Tn{Tn}Tk{Tk}"
    head_file_dir = f"{build_dir}/headfiles/matmul_hls_tile_M{M}_N{N}_K{K}_Tm{Tm}Tn{Tn}Tk{Tk}"
    solution_name = f"sol_Tm{Tm}_Tn{Tn}_Tk{Tk}"            

    os.environ["HLS_SOLUTION"] = solution_name
    if os.path.isfile(f"{build_dir}/{hls_proj_dir}/{solution_name}/syn/report/csynth.rpt"):
        print("exist")
        sema.release()
        return

    os.environ["HLS_HEAD_DIR"] = head_file_dir
    os.environ["HLS_HEAD_FILE"] = f"{head_file_dir}/matmul_tile.h"

    os.environ["HLS_PROJ_DIR"] = hls_proj_dir

    if not os.path.exists(head_file_dir):
        os.makedirs(head_file_dir)
    with open(f"{root_dir}/IP/src/matmul_tile_template.h", mode="r") as fr, open(f"{head_file_dir}/matmul_tile.h", mode="w") as fw:
        for line in fr:
            fw.write(line)
            if "BEGIN DEFINE" in line:
                fw.write(f"const int Tm = {Tm};\n")
                fw.write(f"const int Tn = {Tn};\n")
                fw.write(f"const int Tk = {Tk};\n")
                fw.write(f"const int TCm = {(M-1)//Tm+1};\n")
                fw.write(f"const int TCn = {(N-1)//Tn+1};\n")
                fw.write(f"const int TCk = {(K-1)//Tk+1};\n")
    os.chdir(build_dir)
    subprocess.run(["vitis_hls", f"{root_dir}/IP/src/hls_tile.tcl"])
    sema.release()

def get_metrics(report_file):
    with open(report_file, 'r') as f:
        for line in f:
           if "|+ matmul_tile" in line:
                data = line.split("|")
                latency = int(data[4]) 
                bram, dsp, ff, lut = data[10:14]
                bram_num, bram_pct = re.findall("[0-9]+", bram)
                dsp_num, dsp_pct = re.findall("[0-9]+", dsp)
                ff_num, ff_pct = re.findall("[0-9]+", ff)
                lut_num, lut_pct = re.findall("[0-9]+", lut)
                bram_pct, dsp_pct, ff_pct, lut_pct = int(bram_pct), int(dsp_pct), int(ff_pct), int(lut_pct)
                break
    return latency, bram_pct, dsp_pct, ff_pct, lut_pct

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-ilp_sol', type=str, required=True)
    parser.add_argument('-expert_file', type=str, required=True)
    parser.add_argument('-validation', action="store_true")
    parser.add_argument('-start_line', type=int, required = True) #This should be multiple of number of layers in the switch transformer
    parser.add_argument('-ip_capacity', type=int, required = True)
    parser.add_argument('-baseline', action='store_true')
    parser.add_argument('-build_dir', type=str, required=True)
    parser.add_argument('-ip_candidates_file', type=str, required = True)
    parser.add_argument('-Tm', type=int)
    parser.add_argument('-Tn', type=int)
    parser.add_argument('-Tk', type=int)
    args = parser.parse_args()

    build_dir = args.build_dir
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    expert_list, n_layer, n_experts = generate_expert_list(args.expert_file, args.start_line)
    #ip_candidates = generate_IP_list(f"{root_dir}/build/ip_candidates.log")
    ip_file_name = args.ip_candidates_file #f"{build_dir}/ip_candidates.capacity{args.ip_capacity}.prune.log"
    ip_candidates = generate_IP_list(ip_file_name)

    selected_ips = dict() #key: IP. value: number of copies
    expert_mapping =  dict() #{n_layer: {n_ip: expert_id}}

    generate_selected_ips(args.ilp_sol, ip_file_name, selected_ips, expert_mapping)
    modeling_lat = generate_modeling_latency(args.ilp_sol)

    #generate IPs
    processes = []
    concurrency = 10
    os.environ["HLS_SRC_DIR"] = f"{root_dir}/IP/src"
    sema = Semaphore(concurrency)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    #os.chdir(f'{root_dir}/IP/script')
    idx = 0
    for l, e_dict in expert_mapping.items():
        for (i, j), e_list in e_dict.items():
            for e in e_list:
                M= int(expert_list[l][e].batch_size)
                for N, K in [(3072, 768), (768, 3072)]:
                    if(not args.baseline):
                        Tm, Tn, Tk = int(ip_candidates[i].Tm), int(ip_candidates[i].Tn), int(ip_candidates[i].Tk)
                    else:
                        Tm, Tn, Tk = args.Tm, args.Tn, args.Tk
                    p = Process(target=hls_fun, args=(idx, build_dir, root_dir, M, N, K, Tm, Tn, Tk, sema))
                    processes.append(p)
                    idx+=1

    # inside main process, wait for all processes to finish
    i = 0
    concurrent_processes = 128
    for j in range((len(processes)+127)//128):
        for i in range(128):
            if j*128+i < len(processes):
                processes[j*128 + i].start()
        for i in range(128):
            if j*128+i < len(processes):
                processes[j*128+ i].join()
                processes[j*128+i].close()

    dsp = lut = bram = ff = total_latency = 0
    if not args.baseline:
        for l, e_dict in expert_mapping.items():
            max_latency = 0
            for (i, j), e_list in e_dict.items():
                latency = 0
                resource_added = False
                for e in e_list:
                    print('l, i, j, e', l, i, j, e)
                    M= int(expert_list[l][e].batch_size)
                    for N, K in [(3072, 768), (768, 3072)]:
                        Tm, Tn, Tk = int(ip_candidates[i].Tm), int(ip_candidates[i].Tn), int(ip_candidates[i].Tk)
                        hls_proj_dir = f"matmul_hls_tile_M{M}_N{N}_K{K}_Tm{Tm}Tn{Tn}Tk{Tk}"
                        solution_name = f"sol_Tm{Tm}_Tn{Tn}_Tk{Tk}"            
                        report_file = f"{build_dir}/{hls_proj_dir}/{solution_name}/syn/report/csynth.rpt";
                        assert os.path.isfile(report_file)
                        cur_lat, cur_bram, cur_dsp, cur_ff, cur_lut = get_metrics(report_file)
                        latency += cur_lat
                        print("latency, cur_lat", latency, cur_lat)
                        if not resource_added and l == 0:
                            resource_added = True
                            bram += cur_bram
                            dsp += cur_dsp
                            lut += cur_lut
                            ff += cur_ff
                max_latency = max(latency, max_latency)
                print("max_latency", max_latency)
            total_latency += max_latency
    else:
        Tm, Tn, Tk = args.Tm, args.Tn, args.Tk#512, 1728, 256
        for l in range(6): #TODO: Hardcoded
            for e in range(8): #TODO Hardcoded
                M= int(expert_list[l][e].batch_size)
                for N, K in [(3072, 768), (768, 3072)]:
                    hls_proj_dir = f"matmul_hls_tile_M{M}_N{N}_K{K}_Tm{Tm}Tn{Tn}Tk{Tk}"
                    solution_name = f"sol_Tm{Tm}_Tn{Tn}_Tk{Tk}"            
                    report_file = f"{build_dir}/{hls_proj_dir}/{solution_name}/syn/report/csynth.rpt";
                    print("report_file", report_file)
                    assert os.path.isfile(report_file)
                    cur_lat, bram, dsp, ff, lut = get_metrics(report_file)
                    total_latency += cur_lat

    print("total_latency, bram, dsp, lut, ff", total_latency, bram, dsp, lut, ff)
    print("modeling_latency", modeling_lat)

