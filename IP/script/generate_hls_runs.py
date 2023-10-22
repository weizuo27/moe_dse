import argparse
import os
import subprocess
from multiprocessing import Process, Semaphore
import math

def hls_fun(proc_num, build_dir, root_dir, M, N, K, Tm, Tn, Tk, sema):
    sema.acquire()
    print(f"Process {proc_num}: M, N, K = {M}, {N}, {K}; Tm, Tn, Tk = {Tm}, {Tn}, {Tk}\n")
    hls_proj_dir = f"matmul_hls_tile_Tm{Tm}Tn{Tn}Tk{Tk}"
    head_file_dir = f"{build_dir}/headfiles/Tm{Tm}Tn{Tn}Tk{Tk}"
    solution_name = f"sol_Tm{Tm}_Tn{Tn}_Tk{Tk}"            

    os.environ["HLS_SOLUTION"] = solution_name
    if os.path.isfile(f"{build_dir}/{hls_proj_dir}/{solution_name}/syn/report/csynth.rpt"):
        print(f"{build_dir}/{hls_proj_dir}/{solution_name}/syn/report/csynth.rpt", "exist")
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
            
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-M', type=int, required=True) #M dim
    parser.add_argument('-N', type=int, required=True) #N dim
    parser.add_argument('-K', type=int, required=True) #K dim
    parser.add_argument('-build_dir', type=str, required=True) #The directory in which all the HLS generated IP are.

    #below arguments are only used if -final is set to be true

    #If it is final, it is to generate one HLS with the specified Tm, Tn, Tk. O.w., it is generate sampled Tm, Tn, Tk cross entire design space.
    parser.add_argument('-final', action="store_true") 
    parser.add_argument('-Tm', type=int, required=False)
    parser.add_argument('-Tn', type=int, required=False)
    parser.add_argument('-Tk', type=int, required=False)

    
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    args = parser.parse_args()
    M = args.M
    N = args.N
    K = args.K
    final = args.final

    build_dir = args.build_dir
    #build_dir = f"{root_dir}/build/hls2/M{M}_N{N}_K{K}"

    if final:
        print("final")
        design_space = [(args.Tm, args.Tn, args.Tk)]
    else:
        print("DSE")
        const_M_interval = 8
        N_interval = 64
        Tk = 256
        M_interval = const_M_interval
        design_space = set()
        next_pow_2_M = pow(2, math.ceil(math.log(M)/math.log(2)));

        for Tm in range(M_interval, next_pow_2_M+M_interval, M_interval):
            if next_pow_2_M%Tm == 0:
                for Tn in range(N_interval, N+N_interval, N_interval):
                    if Tn < 3072:
                    #if N % Tn == 0 and Tn < 3072:
                        design_space.add((Tm, Tn, Tk))
    print(len(design_space))
    print(design_space)
    
    os.environ["HLS_SRC_DIR"] = f"{root_dir}/IP/src"

    concurrency = 40
    sema = Semaphore(concurrency)
    processes = []
    i = 0
    for Tm, Tn, Tk in design_space:
        p = Process(target=hls_fun, args=(i, build_dir, root_dir, M, N, K, Tm, Tn, Tk, sema))
        processes.append(p)
        i+=1

    # inside main process, wait for all processes to finish
    i = 0
    concurrent_processes = 256
    for j in range((len(processes)+255)//256):
        for i in range(256):
            if j*256+i < len(processes):
                processes[j*256 + i].start()
        for i in range(256):
            if j*256+i < len(processes):
                processes[j*256+ i].join()
                processes[j*256+i].close()

