import math
from utils import generate_selected_ips, generate_modeling_latency
import subprocess
import argparse
import sys
import os

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-ip_capacity', type=int, required=True)
    parser.add_argument('-n_layer', type=int, required=True)
    parser.add_argument('-build_dir', type=str, required=True)
    args = parser.parse_args()
    build_dir = args.build_dir
    tolerance = 1.0e-4

    num_ip_candidates = 30 #This can be adjusted, the more, the slower

    for l in range(args.n_layer):
        ip_candidates_file = f"{build_dir}/ip_candidates.capacity{args.ip_capacity}.filter_layer{l}.log"
        if os.path.isfile(ip_candidates_file):
            import sys; sys.stdout.flush()
            print(ip_candidates_file, "exist, continiue ...", "\n\n\n")
            import sys; sys.stdout.flush()
            continue
        #import sys; sys.stdout.flush()
        #print("Start Layer", l, "\n\n\n")
        #import sys; sys.stdout.flush()
        with open(f"{build_dir}/ip_candidates_new.log", mode='r') as fr, open(ip_candidates_file, mode='w') as fw:
            r_lines = fr.readlines()
            total_num_ips = len(r_lines)
            interval = math.ceil(total_num_ips/num_ip_candidates)
            selected_lines = r_lines[0:total_num_ips:interval]
            for idx, ln in enumerate(selected_lines):
                fw.write(ln)

        selected_ips = dict()
        ips_with_margin = set()
        idx = 0
        lat_old = None

        while(True):
            import sys; sys.stdout.flush()
            print("python", "ilp_solver2.py", "-start", str(l), "-n_layer", 
                "1",  "-ilp_run", "0", "-ip_candidates_file", ip_candidates_file,
                "-ip_capacity",  str(args.ip_capacity),
                '-build_dir', build_dir
                )
            import sys; sys.stdout.flush()
            selected_ips.clear()
            subprocess.run(["python", "ilp_solver2.py", "-start", str(l), "-n_layer", 
                "1",  "-ilp_run", "0", "-ip_candidates_file", ip_candidates_file,
                "-ip_capacity",  str(args.ip_capacity),
                '-build_dir', build_dir
                ])
            sol_f = f"{build_dir}/ilp_sol/opt.capacity{args.ip_capacity}.sol0.layer{l}.sol"
            lat = generate_modeling_latency(sol_f)

            import sys; sys.stdout.flush()
            print("lat = ", lat, "lat_old =", lat_old, "\n\n")
            assert(lat >= 100 and lat_old is None or lat <=lat_old*(1+tolerance))
            import sys; sys.stdout.flush()
            if lat_old is not None and abs((lat_old-lat)/lat_old) <= tolerance:
                break

            generate_selected_ips(sol_f, ip_candidates_file, selected_ips, None)
            margin = int((num_ip_candidates/len(selected_ips))//2)
            ips_with_margin.clear()

            with open(ip_candidates_file, mode='r') as fr:
                r_lines1 = fr.readlines()
                for selected_ip in selected_ips.keys():
                    ip = r_lines1[selected_ip]
                    ip_id = int(ip.split()[0])
                    for i in range(max(0, ip_id - margin), min(total_num_ips, ip_id+margin)):
                        ips_with_margin.add(i)

            ips_with_margin_list = list(ips_with_margin)
            ips_with_margin_list = sorted(ips_with_margin_list)
            #print(len(ips_with_margin_list), ips_with_margin_list)
            
            with open(ip_candidates_file, mode='w') as fw:
                for i in ips_with_margin_list:
                    fw.write(r_lines[i])

            lat_old = lat
            idx += 1
