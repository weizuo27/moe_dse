import math
import re
import os

def compute_latency(expert, ip):
    num_Current_M_blocks = math.ceil(expert.batch_size /ip.Tm)
    latency = ip.lat_per_iter * num_Current_M_blocks 
    return latency

class IP:
    def __init__(self, ip_id, M, N, K, Tm, Tn, Tk, Lat_per_iter, dsp_pct, lut_pct):
        self.M = int(M)
        self.Tm = int(Tm)
        self.Tn = int(Tn)
        self.Tk = int(Tk)
        self.lat_per_iter = Lat_per_iter
        self.lut = int(lut_pct)
        self.dsp = int(dsp_pct)
        self.max_num_copies = min(int(100//self.dsp), int(100//self.lut))
        self.id = ip_id
    def __str__(self):
        return f"IP object, max {self.max_num_copies} copies. latency: {self.lat}, {self.lat_per_iter}, {self.M}, {self.Tm}, {self.Tn}, {self.Tk}, lut percentage: {self.lut}, dsp percentage: {self.dsp}"

class Expert:
    def __init__(self, batch_size):
        self.batch_size = batch_size
    def __str__(self):
        return f"Expert, batch size = {self.batch_size}"

def generate_expert_list(expert_count_file, start_line = 0):
    batch_size_list = list()
    idx = 0
    with open(expert_count_file, mode = 'r') as f:
        for line in f:
            if idx < start_line:
                continue
            if idx >= start_line + 6: #TODO: Hard code n_layer
                break
            experts_per_layer = re.findall("[0-9]+\.*[0-9]*", line)[1:]# re.findall("[0-9]+\.[0-9]+", line)
            assert(len(experts_per_layer)) == 8 #TODO: hardcoded
            experts_per_layer = list(map(int, [x+0.5 for x in list(map(float, experts_per_layer))]))
            batch_size_list.append(experts_per_layer)
            idx+=1

    n_experts = len(batch_size_list[0])
    n_layer = len(batch_size_list)
    expert_list = list()
    for l in range(n_layer):
        expert_list_tmp = list()
        for e in range(n_experts):
            expert_list_tmp.append(Expert(batch_size_list[l][e]))
        expert_list.append(expert_list_tmp) 

    return expert_list, n_layer, n_experts

def generate_IP_list(ip_candiates_file):
    ip_candidates = list()
    #with open(f"{root_dir}/build/ip_candidates.log", mode='r') as fr:
    with open(ip_candiates_file, mode='r') as fr:
        for line in fr:
            resource = list(map(float, line.split()))
            ip_id = int(resource[0])
            resource = resource[1:7] + resource[8:]
            ip_candidates.append(IP(ip_id, *resource))
    return ip_candidates

def generate_selected_ips(ilp_sol_file, ip_candiates_file, selected_ips,  expert_mapping):
    #selected_ips = dict() #key: IP. value: number of copies
    #expert_mapping =  dict() #{n_layer: {n_ip: expert_id}}
    with open(ilp_sol_file, 'r') as f:
        for line in f:
            if 'x_' in line:
                ij, selected = line.split()
                selected = round(float(selected))
                i, j= map(int, re.findall("[0-9]+", ij))

                if selected == 1:
                    if i not in selected_ips:
                        selected_ips[i] = 1
                    else:
                        selected_ips[i] += 1

            if expert_mapping is not None:
                if 'y_' in line:
                    leij, selected = line.split()
                    selected = round(float(selected))
                    l, e, i, j = map(int, re.findall("[0-9]+", leij))
                    if selected:
                        if l not in expert_mapping:
                            expert_mapping[l] = dict({(i, j):[e]})
                        elif (i, j) not in expert_mapping[l]:
                            expert_mapping[l][(i, j)] = [e]
                        else:
                            expert_mapping[l][(i,j)].append(e)

def generate_modeling_latency(ilp_sol_file):
    lat = 0
    with open(ilp_sol_file, 'r') as f:
        for l in f:
            if "ss_" not in l:
                continue
            lat += int(math.ceil(float(l.split()[1])))
            #lat += int(re.findall("[0-9]+", l)[-1])
    return lat

def get_ip_ids(ip_candiates_file):
    selected_ip_ids = set()

    with open(ip_candiates_file, 'r') as f:
        for r_line in f:
            ip_id = (r_line.split())[0]
            selected_ip_ids.add(int(ip_id))
    return selected_ip_ids
