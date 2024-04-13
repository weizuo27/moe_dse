import re
import os
import math
import numpy as np

def is_pareto_efficient(costs, return_mask = True, margin = 0.0):
    """
    Find the pareto-efficient points
    :param costs: An (n_points, n_costs) array
    :param return_mask: True to return a mask
    :return: An array of indices of pareto-efficient points.
    If return_mask is True, this will be an (n_points, ) boolean array
    Otherwise it will be a (n_efficient_points, ) integer array of indices.
    """
    is_efficient = np.arange(costs.shape[0])
    n_points = costs.shape[0]
    next_point_index = 0  # Next index in the is_efficient array to search for
    while next_point_index<len(costs):
        nondominated_point_mask = np.any(costs< (1-margin)*costs[next_point_index], axis=1)
        nondominated_point_mask[next_point_index] = True
        is_efficient = is_efficient[nondominated_point_mask]  # Remove dominated points
        costs = costs[nondominated_point_mask]
        next_point_index = np.sum(nondominated_point_mask[:next_point_index])+1
    if return_mask:
        is_efficient_mask = np.zeros(n_points, dtype = bool)
        is_efficient_mask[is_efficient] = True
        return is_efficient_mask
    else:
        return is_efficient



#costs = np.array([[2.0,3.0, 0.0], [1.0,4.0, 1.0], [2.0,2.0, 1.0], [3.0,1.0, 1.0]])
#print(costs)
#print(is_pareto_efficient(costs, return_mask = True))

if __name__ == '__main__':
    print("in main")
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    build_dir = f"{root_dir}/build"
    #
    costs_list = []
    #
    N_const = 3072
    K_const = 768
    
    with open(f"{build_dir}/ip_csv.log", "r") as fr:
        for line in fr:
            M, N, K, Tm, Tn, Tk, Lat, dsp, lut, dsp_pct, lut_pct = list(map(int, line.split(",")))
            Lat_iter = Lat / (math.ceil(M/Tm)) / (math.ceil(N/Tn)) / (math.ceil(K/Tk))
            Lat_M_iter = Lat_iter * (math.ceil(N_const/Tn) * math.ceil(K_const/Tk) + math.ceil(K_const/Tn) * math.ceil(N_const/Tk))
            costs_list.append([M, N, K, Tm, Tn, Tk, -Tm, Lat_M_iter, dsp_pct, lut_pct])
    
    costs = np.array(costs_list)
    #with open(f"{root_dir}/build/ip_csv_raw.log", mode ='w') as f:
    #    for ip in costs_list:
    #        out = " ".join(str(i) for i in ip)
    #        f.write(out+"\n")
    
    pareto_mask = is_pareto_efficient(costs[:,6:], return_mask = True)
    pareto_cost_array = costs[pareto_mask]
    
    mask = is_pareto_efficient(pareto_cost_array[:,6:], margin = 0.01)
    approx_pareto_array = pareto_cost_array[mask].tolist()
    sorted_approx_pareto = (sorted(approx_pareto_array, key=lambda x: math.ceil(x[7]/x[3])))
    
    with open(f"{root_dir}/build/ip_candidates.log", mode ='w') as f:
        for ip in sorted_approx_pareto:
            out = " ".join(str(i) for i in ip)
            f.write(out+"\n")
    
    
    
    
    
