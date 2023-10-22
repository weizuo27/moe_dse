import re
import argparse
import ast
import numpy as np
import os
#fin: layer_log  | validation_log
#fout: expert_count.log | validation_expert_count.log

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-fin', type=str, required=True)
    parser.add_argument('-fout', type=str, required=True)
    parser.add_argument('-validation', action="store_true")

    args = parser.parse_args()

    table = dict() #layer_id: expert_distribution
    
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alpha = 2
    
    with open(args.fin, mode="r") as f:
        for line in f:
            if "layer_id" in line:
                layer_id = int(re.search("[0-9]+", re.search("layer_id  [0-9]+", line).group(0)).group(0))
                batch_size = int(re.search("[0-9]+", re.search("torch.Size.*[0-9]+,", line).group(0)).group(0))
                expert_dist = ast.literal_eval(re.search("\[.*\]", re.search('tensor\(\[.*\]', line).group(0)).group(0))
                if layer_id in table:
                    table[layer_id].append(expert_dist)
                else:
                    table[layer_id] = [expert_dist]
    
    print(table.keys())
    #calculate the mean and variance
    #with open(f"{root_dir}/build/{args.fout}", mode = 'w') as f:
    total_outlier = 0
    total_entries = 0
    if not args.validation:
        #with open(args.fout, mode = 'w') as f:
            for i in table:
                table[i] = np.array(table[i])
                var = np.var(table[i], axis = 0)
                mean = np.mean(table[i], axis = 0)
                print(mean)
                stdv = np.std(table[i], axis = 0)
                out = " ".join(map(str,(mean+ alpha * stdv)))
                #f.write(f"layer {i}: {out}\n")
            for vec in table[i]:
                within_range_arr = (vec <= mean + alpha * stdv)
                #if (sum(within_range_arr) <4):
                total_outlier+= (8-sum(within_range_arr))
                total_entries += 8
                #print(within_range_arr, 8-sum(within_range_arr))
    print(total_outlier, total_entries, float(total_outlier)/total_entries)

    #else:
    #    with open(args.fout, mode = 'w') as f:
    #        for j in range(len(table[1])):
    #            for i in table:
    #                out = " ".join(map(str,(table[i][j])))
    #                f.write(f"layer {i}: {out}\n")
            
        
