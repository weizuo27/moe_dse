import gurobipy as gp
import argparse
import os
from gurobipy import GRB
from utils import generate_expert_list, generate_IP_list, compute_latency
import math
import sys

BIG_NUM = 1000000000 #This needs to be bigger than the worst case latency: the latency if all are mapped to the slowest IP. But cannot be too big.

def generate_latency_table(expert_list, ip_candidates, n_layer):
    latency_table = list()
    for l in range(n_layer):
        latency_table_l = list()
        for e in range(n_experts):
            latency_table_e = list()
            for i in range(len(ip_candidates)):
                ip = ip_candidates[i]
                expert = expert_list[l][e]
                #latency_table_e.append(compute_latency(expert, ip, is_first_matmul=True)+compute_latency(expert, ip, is_first_matmul=False))
                latency_table_e.append(compute_latency(expert, ip))
                #print("expert ", expert, latency_table_e[-1])
            latency_table_l.append(latency_table_e)
        latency_table.append(latency_table_l)
    #for l in range(n_layer):
    #    for e in range(n_experts):
    #        for i in range(len(ip_candidates)):
    #            print(f"second l, e, i = {l}, {e}, {i}, latency = {latency_table[l][e][i]}\n")
    return latency_table

def ILP(ip_candidates, n_layer, n_experts, latency_table, ilp_run, lat_ub, ip_capacity, margin):
    print("ilp_run", ilp_run)
    # Create a new model
    m = gp.Model("mip1")
    m.setParam("Threads", 20);
    #m.Params.IterationLimit = 100
    if ilp_run == 1:
        m.Params.timelimit = 3600

    if ilp_run == 1:
        m.Params.SolutionLimit = 1

    # Create variables
    x = list() #a list of integer variables: x_ij: the j-th copy of ip I is selected
    for i in range(len(ip_candidates)):
       x_tmp = list()
       for j in range(ip_candidates[i].max_num_copies):
           x_tmp.append(m.addVar(vtype=GRB.BINARY, name=f"x_i{i}j{j}"))
       x.append(x_tmp)

    y = list() #y_leij: the l-th layer, e-th expert, mapped to i-th IP, j-th copy
    for l in range(n_layer):
        y0 = list()
        for e in range(n_experts):
            y00 = list()
            for i in range(len(ip_candidates)):
                y000 = list()
                for j in range(ip_candidates[i].max_num_copies):
                    y000.append(m.addVar(vtype=GRB.BINARY, name = f"y_l{l}e{e}i{i}j{j}"))
                y00.append(y000)
            y0.append(y00)
        y.append(y0)


    #scheduling variable. The start time of l-th layer, e-th expert
    s = list()
    for l in range(n_layer):
        s0 = list()
        for e in range(n_experts):
            s0.append(m.addVar(vtype=GRB.INTEGER, name = f"s_{l}{e}"))
        s.append(s0)

    ss = list()
    for l in range(n_layer):
        ss.append(m.addVar(vtype=GRB.INTEGER, name = f"ss_{l}"))

    ## Add constraint:
    #0. If baseline, only 1 IP is selected
    if ilp_run == 2:
        ip_list = []
        for i in range(len(ip_candidates)):
            ip = ip_candidates[i]
            for j in range(ip.max_num_copies):
                ip_list.append((1, x[i][j]))
        m.addConstr(gp.LinExpr(ip_list) == 1, 'baseline constraint')

    ##1. IP should not exceed resource limit. TODO: I assume no need to add constraints that each resource should not exceed max copy
    lut_list = list()
    dsp_list = list()
    for i in range(len(ip_candidates)):
        ip = ip_candidates[i]
        for j in range(ip.max_num_copies):
            lut_list.append((ip.lut, x[i][j]))
            dsp_list.append((ip.dsp, x[i][j]))

    lut_expr = gp.LinExpr(lut_list)
    dsp_expr = gp.LinExpr(dsp_list)

    m.addConstr(lut_expr <= ip_capacity, "c_lut_capacity")
    m.addConstr(dsp_expr <= ip_capacity, "c_dsp_capacity")


    #2. For each layer, each expert can only map to 1 IP.
    for l in range(n_layer):
        for e in range(n_experts):
            ip_per_expert_list = list()
            for i in range(len(ip_candidates)):
                num_copies = ip_candidates[i].max_num_copies
                for j in range(num_copies):
                    ip_per_expert_list.append((1, y[l][e][i][j]))
            m.addConstr(gp.LinExpr(ip_per_expert_list) == 1, f"ip_per_expert_list_l{l}_e{e}")


    #3. If x_ij is not selected, then the correpsonding y_leij should also be 0
    #if x_ij is selected, then at least one y_leij should be 1
    for i in range(len(ip_candidates)):
        num_copies = ip_candidates[i].max_num_copies
        for j in range(num_copies):
            #lhs = list()
            for l in range(n_layer):
                lhs_per_layer  = list()
                for e in range(n_experts):
                    #lhs.append((1, y[l][e][i][j]))
                    lhs_per_layer.append((1, y[l][e][i][j]))

                expr_rhs_lb = gp.LinExpr(1, x[i][j])
                m.addConstr(gp.LinExpr(lhs_per_layer)>= expr_rhs_lb, f"l{l}b_y_le_x_i{i}_j{j}")
                m.addConstr(gp.LinExpr(lhs_per_layer) <= gp.LinExpr(n_experts, x[i][j]))

            #expr_lhs = gp.LinExpr(lhs)
            #expr_rhs_ub = gp.LinExpr(n_layer*n_experts, x[i][j])
            #m.addConstr(expr_lhs<= expr_rhs_ub, f"ub_y_le_x_i{i}_j{j}")


    #5: Resource: For each layer, if two experts map to the same resource, the inteval of their start time
    # (2-y1-y2)*M + (S1-S0) +M*Var > L0
    # (2-y1-y2)*M + (S0-S1) + M*(1-Var) > L1
    for l in range(n_layer):
        for e0 in range(n_experts):
            for e1 in range(e0+1, n_experts):
                for i in range(len(ip_candidates)):
                    num_copies = ip_candidates[i].max_num_copies
                    for j in range(num_copies):
                        #y, e0 -> y, e1
                        m.addConstr( (2-y[l][e1][i][j] - y[l][e0][i][j]) * BIG_NUM + (s[l][e1] - s[l][e0]) >= latency_table[l][e0][i], f"resource_constr0_{l}{e0}{e1}{i}{j}")

    #6: For each layer, sink node should be later than y nodes
    for l in range(n_layer):
        for e in range(n_experts):
            lhs = list()
            for i in range(len(ip_candidates)):
                num_copies = ip_candidates[i].max_num_copies
                for j in range(num_copies):
                    lhs.append((latency_table[l][e][i], y[l][e][i][j]))
            m.addConstr(ss[l] >= s[l][e]+gp.LinExpr(lhs))

    #optimizations:
    ss_list = list()
    for l in range(n_layer):
        ss_list.append((1, ss[l]))

    #for i in range(len(ip_candidates)):
    #    num_copies = ip_candidates[i].max_num_copies
    #    for j in range(num_copies):
    #        ss_list.append(((ip_candidates[i].dsp + ip_candidates[i].lut), x[i][j]))
        
    ss_list_expr = gp.LinExpr(ss_list)
    if ilp_run == 1:
        m.addConstr(ss_list_expr <= lat_ub*margin)
        #m.addConstr(ss_list_expr <= 39675778*1.05)

    m.setObjective(ss_list_expr, GRB.MINIMIZE)
    m.update()
    print (m.NumVars)
    m.write('out.lp')

    # Optimize model
    m.optimize()

    if m.Status != 9 and m.Status != 3: #9: Timeout, 3: Infeasible
        for v in m.getVars():
            if "y" in v.VarName:
                if v.X == 1.0:
                    print('%s %g' % (v.VarName, v.X))
            if f"ss_{n_layer-1}" in v.VarName:
                    print('%s %g' % (v.VarName, v.X))
        #print('Obj: %g' % m.ObjVal)
    return m


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-start', type=int, required = True)
    parser.add_argument('-n_layer', type=int)
    parser.add_argument('-ilp_run', type = int, required = True, help="0: dse optimality run, 1: dse feasibility run, 2: baseline run")
    parser.add_argument('-lat_ub', type=int)
    parser.add_argument('-ip_candidates_file', type=str, required = True)
    parser.add_argument('-ip_capacity', type=int)
    parser.add_argument('-lat_margin', type=float)
    parser.add_argument('-build_dir', type=str, required=True)


    args = parser.parse_args()
    build_dir = args.build_dir

    assert(args.ilp_run >=0 and args.ilp_run <3)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    expert_list, n_layer, n_experts = generate_expert_list(f"{build_dir}/expert_count.log")

    ip_candidates = generate_IP_list(args.ip_candidates_file)

    start = args.start
    if args.n_layer is not None:
        n_layer = args.n_layer

    print("n_layer", n_layer, "start", start)
    latency_table = generate_latency_table(expert_list[start:start+n_layer], ip_candidates, n_layer)

    lat_margin = args.lat_margin
    next_run = True
    while(next_run): 
        import sys; sys.stdout.flush();
        print("\n\nlat_margin = ", lat_margin, "\n\n")
        import sys; sys.stdout.flush();
        if(args.ilp_run == 1 and lat_margin >= 1.11):
            sys.exit(3) #Fake infeasible
        m = ILP(ip_candidates, n_layer, n_experts, latency_table, args.ilp_run, args.lat_ub, args.ip_capacity, lat_margin)
        import sys; sys.stdout.flush();
        print("m status", m.Status)
        import sys; sys.stdout.flush();
        if m.Status == 9 and args.ilp_run==1: #Timeout
            lat_margin += 0.01
            next_run = True
        else:
            next_run = False

    if args.ilp_run != 1:
        assert(m.Status == 2)
    if args.ilp_run == 0:
        prefix = "opt"
    elif args.ilp_run == 1:
        prefix = "fes"
    else:
        prefix = "baseline"

    for i in range(m.SolCount):
        m.Params.SolutionNumber = i
        m.write(f"{build_dir}/ilp_sol/{prefix}.capacity{args.ip_capacity}.sol{i}.layer{start}.sol")
    print("lat_margin at exit =", lat_margin)
    sys.exit(m.Status)
