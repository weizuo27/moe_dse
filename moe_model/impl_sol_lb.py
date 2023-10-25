import re
import argparse
import subprocess
from utils import generate_IP_list
import os
def generate_selected_ips(ilp_sol_files, ip_candiates_files, selected_ips):
    for ilp_sol_file, ip_candiates_file in zip(ilp_sol_files, ip_candiates_files):
        with open(ip_candiates_file, 'r') as ip_file:
            ip_candidates = ip_file.readlines()

        selected_ips_per_layer = dict()

        with open(ilp_sol_file, 'r') as f:
            for line in f:
                if 'x_' in line:
                    ij, selected = line.split()
                    selected = round(float(selected))
                    if selected != 1:
                        continue
                    i, j= map(int, re.findall("[0-9]+", ij))
                    selected_line = ip_candidates[i]
                    selected_ip_id = selected_line.split()[0]

                    if selected_ip_id in selected_ips_per_layer:
                        selected_ips_per_layer[selected_ip_id] += 1
                    else:
                        selected_ips_per_layer[selected_ip_id] = 1
        print(selected_ips_per_layer)
        for k, v in selected_ips_per_layer.items():
            if k in selected_ips:
                if selected_ips[k] <= v:
                    selected_ips[k] = v
            else:
                selected_ips[k] = v
    print(selected_ips)

def generate_ip_lb_file(ip_lb_file):
    if not os.path.isfile(ip_lb_file):
        n_layer = 6

        ip_candiates_files = [f"/mnt/shared/home/weizuo/moe_dse/IP/build4/ip_candidates.capacity80.filter_layer{x}.log" for x in range(n_layer)]
        ilp_sol_files = [f"/mnt/shared/home/weizuo/moe_dse/IP/build4/ilp_sol/opt.capacity80.sol0.layer{x}.sol" for x in range(n_layer)]

        selected_ips = dict()
        generate_selected_ips(ilp_sol_files, ip_candiates_files, selected_ips)

        ip_candidate_csv = f"/mnt/shared/home/weizuo/moe_dse/IP/build4/ip_candidates_new.log"
        with open(ip_candidate_csv, 'r') as f:
            ip_csv = f.readlines()

        with open(ip_lb_file, 'w') as fw:
            for k in selected_ips.keys():
                ip_candidate_line = ip_csv[int(k)]
                fw.write(ip_candidate_line)
    else:
        print(ip_lb_file, "exist")

def run_hls(Tm, Tn, Tk, root_dir, hls_proj_dir):
    os.environ["HLS_SRC_DIR"] = f"{root_dir}/IP/src"
    head_file_dir = f"{build_dir}/headfiles/lb_Tm{Tm}Tn{Tn}Tk{Tk}"

    os.environ["HLS_SOLUTION"] = "sol"
    if os.path.isfile(f"{build_dir}/{hls_proj_dir}/sol/syn/report/csynth.rpt"):
        print(f"{build_dir}/{hls_proj_dir}/sol/syn/report/csynth.rpt", "exist")
        return

    os.environ["HLS_HEAD_DIR"] = head_file_dir
    os.environ["HLS_HEAD_FILE"] = f"{head_file_dir}/matmul_tile.h"

    os.environ["HLS_PROJ_DIR"] = f"{hls_proj_dir}"

    if not os.path.exists(head_file_dir):
        os.makedirs(head_file_dir)
    with open(f"{root_dir}/IP/src/matmul_tile_template.h", mode="r") as fr, open(f"{head_file_dir}/matmul_tile.h", mode="w") as fw:
        for line in fr:
            fw.write(line)
            if "BEGIN DEFINE" in line:
                fw.write(f"const int Tm = {Tm};\n")
                fw.write(f"const int Tn = {Tn};\n")
                fw.write(f"const int Tk = {Tk};\n")
    os.chdir(build_dir)
    subprocess.run(["vitis_hls", f"{root_dir}/IP/src/lb_hls_tiles.tcl"])
    os.chdir("/mnt/shared/home/weizuo/moe_dse/moe_model")

def run_impl(build_dir, hls_proj_dir):
    hls_build_dir = f"{build_dir}/{hls_proj_dir}/sol/impl/verilog" 
    if os.path.isfile(f"{hls_build_dir}/util.rpt"):
        print(f"{hls_build_dir}/util.rpt exist, exit ...")
        return
    subprocess.run(["cp", "/mnt/shared/home/weizuo/moe_dse/moe_model/run_impl.tcl", hls_build_dir])
    os.chdir(hls_build_dir)
    subprocess.run(["vivado", "-mode", "batch", "-source", "./run_impl.tcl"])
    os.chdir("/mnt/shared/home/weizuo/moe_dse/moe_model")

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-line_num_start', type=int, required=True)
    parser.add_argument('-line_num_end', type=int, required=True)
    parser.add_argument('-build_dir', type=str, required=True)
    args = parser.parse_args()
    build_dir = args.build_dir
    line_num_start = args.line_num_start
    line_num_end = args.line_num_end

    ip_lb_file = f"/mnt/shared/home/weizuo/moe_dse/IP/build4/ip_candidates_lb.log"
    generate_ip_lb_file(ip_lb_file)
    ip_list = generate_IP_list(ip_lb_file)

    for line_num in range(line_num_start, line_num_end):
    
        Tm, Tn, Tk = ip_list[line_num].Tm, ip_list[line_num].Tn, ip_list[line_num].Tk

        hls_proj_dir = f"lb_matmul_hls_tile_Tm{Tm}Tn{Tn}Tk{Tk}"
        print("line num", line_num, hls_proj_dir)

        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        run_hls(Tm, Tn, Tk, root_dir, hls_proj_dir)
        run_impl(build_dir, hls_proj_dir)
    









