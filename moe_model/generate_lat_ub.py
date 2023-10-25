#generate lowerbound for last ilp
import re
import argparse
import sys
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-n_layer', type=int, required=True)
    parser.add_argument('-ip_capacity', type=int, required = True)

    args = parser.parse_args()

    total_lat = 0
    for l in range(args.n_layer):
        with open(f"../build/ilp_sol/opt.capacity{args.ip_capacity}.sol0.layer{l}.sol", mode='r') as f:
            last_line = f.readlines()[-1]
            assert("ss_0" in last_line)
            lat = int(re.findall("[0-9]+", last_line)[-1])
            total_lat += lat
    print(total_lat)
    sys.exit(total_lat)



#python ilp_solver2.py -start 0 -n_layer 1 -ilp_run 0
#python ilp_solver2.py -start 1 -n_layer 1 -ilp_run 0 
#python ilp_solver2.py -start 2 -n_layer 1 -ilp_run 0
#python ilp_solver2.py -start 3 -n_layer 1 -ilp_run 0
#python ilp_solver2.py -start 4 -n_layer 1 -ilp_run 0
#python ilp_solver2.py -start 5 -n_layer 1 -ilp_run 0
