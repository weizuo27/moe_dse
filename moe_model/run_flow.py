import subprocess
import sys
import re
import argparse
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-build_dir', type=str, required=True)
    args = parser.parse_args()
    build_dir = args.build_dir

    n_layer = 6
    origin_margin = 1
    for ip_capacity in [30]:#, 30, 20]:
        lat_margin = 1.02
        margin = origin_margin
        sys.stdout.flush()
        sys.stdout.flush()
        idx = 0
        while(True):
            print("\n ip_capacity = ", ip_capacity, "lat_margin = ",  lat_margin, "margin=",margin, "attempt time=", idx, "\n")
            sys.stdout.flush()

            print("\n", 'python filter_ip_candidates.py', '-n_layer', str(n_layer), '-ip_capacity', str(ip_capacity), '-build_dir', build_dir, "\n")
            sys.stdout.flush()
            subprocess.run(['python', 'filter_ip_candidates.py', '-n_layer', str(n_layer), '-ip_capacity', str(ip_capacity), '-build_dir', build_dir])

            sys.stdout.flush()
            print("\n", 'python', 'prune_ip_candidates.py', '-n_layer', str(n_layer), '-ip_capacity', str(ip_capacity), '-margin', str(margin), '-build_dir', build_dir, "\n")
            sys.stdout.flush()
            result = subprocess.run(['python', 'prune_ip_candidates.py', '-n_layer', str(n_layer), '-ip_capacity', str(ip_capacity), '-margin', str(margin), '-build_dir', build_dir])
            if result.returncode == 9: #reached max margin, but still cannot find a solution, then go back to small margin but lossen the lat_margin
                margin = origin_margin
                lat_margin += 0.01
                print("\n cant find solution, increase lat_margin", lat_margin, "\n")
                continue
            total_lat = 0
            for l in range(n_layer):
                with open(f"{build_dir}/ilp_sol/opt.capacity{ip_capacity}.sol0.layer{l}.sol", mode='r') as f:
                    last_line = f.readlines()[-1]
                    assert("ss_0" in last_line)
                    lat = int(re.findall("[0-9]+", last_line)[-1])
                    total_lat += lat
            sys.stdout.flush()

            print('\n', 'python', 'ilp_solver2.py', '-start', '0',
                '-n_layer', str(n_layer), '-ilp_run', '1', '-lat_ub', str(total_lat),
                '-ip_candidates_file', f"{build_dir}/ip_candidates.capacity{ip_capacity}.prune.log", 
                "-ip_capacity", str(ip_capacity), '-lat_margin', str(lat_margin), 
                '-build_dir', build_dir, '\n')
            sys.stdout.flush()
            out_file_name = f"run_log_capacity{ip_capacity}_new_vitis"
            out_file = open(out_file_name, 'a')
            result = subprocess.run(['python', 'ilp_solver2.py', '-start', '0',
                '-n_layer', str(n_layer), '-ilp_run', '1', '-lat_ub', str(total_lat),
                '-ip_candidates_file', f"{build_dir}/ip_candidates.capacity{ip_capacity}.prune.log", 
                "-ip_capacity", str(ip_capacity), '-lat_margin', str(lat_margin), 
                '-build_dir', build_dir], stdout=out_file)
            out_file.close()

            if result.returncode == 3: #infeasible
                sys.stdout.flush()
                print("\n ilp output infeasible, increase margin and rerun the process\n")
                sys.stdout.flush()
                found = False
                with open(out_file_name, 'r') as fr:
                    for line in fr:
                        if "lat_margin at exit" in line:
                            found = True
                            lat_margin = float(line.split(" = ")[-1])
                            break
                if(found):
                    margin += 10
                    print("\n real infeasible, lat_margin is ", lat_margin, "increase margin by 10\n")
                else:
                    margin += 2
                    print("\n fake infeasible, margin reaches the max limit, but still time out, increase margin by 2, and restart with minimal lat_margin", lat_margin, "\n")
                idx += 1
            else:
                break

