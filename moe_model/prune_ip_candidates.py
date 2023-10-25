import os
import re
from utils import generate_selected_ips, get_ip_ids
import argparse
import sys

#Run this script if we want to generate a smaller ip_candidate log, with only the IPs selected by running ILP on single layer
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-n_layer', type=int, required=True)
    parser.add_argument('-ip_capacity', type=int, required = True)
    parser.add_argument('-build_dir', type=str, required=True)
    parser.add_argument('-margin', type=int, required=True)

    args = parser.parse_args()
    build_dir = args.build_dir

    margin = args.margin

    ips = set()

    ip_ids_with_margin = set()
    prune_file_name = f"{build_dir}/ip_candidates.capacity{args.ip_capacity}.prune.log"
    if not os.path.isfile(prune_file_name):
        f = open(prune_file_name, 'w')
        f.close()
    ip_ids_with_margin_old = get_ip_ids(prune_file_name)

    with open(f"{build_dir}/ip_candidates_new.log", mode='r') as fr:
        r_lines_const = fr.readlines()


    for l in range(args.n_layer):
        selected_ips = dict()
        f = f"{build_dir}/ilp_sol/opt.capacity{args.ip_capacity}.sol0.layer{l}.sol"
        ip_candidates_file = f"{build_dir}/ip_candidates.capacity{args.ip_capacity}.filter_layer{l}.log"
        generate_selected_ips(f, ip_candidates_file, selected_ips, None)
        with open(ip_candidates_file, mode='r') as fr:
            r_lines = fr.readlines()
            for selected_ip in selected_ips.keys():
                ip_line = r_lines[selected_ip]
                ip_id = int(ip_line.split()[0])
                ips.add(ip_id)

    for ip in ips:
        for i in range(max(0, ip-margin), min(ip+margin+1, len(r_lines_const))):
            r = r_lines_const[i]
            resource = r.split()
            dsp_pct = resource[-2]
            lut_pct = resource[-1]
            if float(dsp_pct) > float(args.ip_capacity) or float(lut_pct) > float(args.ip_capacity):
                continue
            ip_ids_with_margin.add(i)


    if(ip_ids_with_margin == ip_ids_with_margin_old):
        sys.exit(9)

    with open(prune_file_name, mode='w') as fw:
        for selected_ip in ip_ids_with_margin:
            fw.write(r_lines_const[selected_ip])

