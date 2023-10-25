from utils import generate_IP_list, generate_selected_ips
import subprocess
import os
import argparse

def generate_function_call(idx, fw):
    if(idx > 0):
        fw.write("\n,")
    fw.write(f" DTYPE *A{idx}, hls::vector<IDX_DTYPE, IDX_DSIZE{idx}> *A_indice{idx}\n")
    fw.write(f", hls::vector<IDX_DTYPE, IDX_DSIZE{idx}> *C_indice{idx}\n")
    fw.write(f", hls::vector<DTYPE, DSIZE> *B{idx}, hls::vector<DTYPE, DSIZE> *C{idx}\n")
    fw.write(f", int M{idx}, int N{idx}, int K{idx}, bool relu{idx}\n")



def generate_files(root_dir, impl_dir, hls_proj_dir):
    with open(f"{root_dir}/IP/impl/matmul_tile_template.h", mode="r") as fr, open(f"{impl_dir}/matmul_tile.h", mode="w") as fw:
        for line in fr:
            fw.write(line)
            if "BEGIN DEFINE0" in line:
                idx = -1
                for i, num_copy in selected_ips.items():
                    ip = ip_candidates[i]
                    Tm, Tn, Tk = ip.Tm, ip.Tn, ip.Tk
                    for j in range(num_copy):
                        idx += 1
                        fw.write(f"const int Tm{idx} = {Tm};\n")
                        fw.write(f"const int Tn{idx} = {Tn};\n")
                        fw.write(f"const int Tk{idx} = {Tk};\n")
                        fw.write(f"const int IDX_DSIZE{idx} = (64 / sizeof(IDX_DTYPE) > Tm{idx}) ? Tm{idx} : 64 / sizeof(IDX_DTYPE);\n")
                        fw.write(f"static_assert(Tk{idx} % DSIZE == 0 && Tn{idx} % DSIZE == 0); //The column of B should be dividable by DSIZE \n\n")
            if "BEGIN DEFINE1" in line:
                idx = -1
                for i, num_copy in selected_ips.items():
                    ip = ip_candidates[i]
                    for j in range(num_copy):
                        idx += 1
                        generate_function_call(idx, fw)

    with open(f"{root_dir}/IP/impl/matmul_tile_template.cpp", mode="r") as fr, open(f"{impl_dir}/matmul_tile.cpp", mode="w") as fw:
        for line in fr:
            fw.write(line)
            if "BEGIN DEFINE0" in line:
                idx = -1
                for i, num_copy in selected_ips.items():
                    ip = ip_candidates[i]
                    for j in range(num_copy):
                        idx += 1
                        generate_function_call(idx, fw)
            if "BEGIN DEFINE1" in line:
                idx = -1
                for i, num_copy in selected_ips.items():
                    ip = ip_candidates[i]
                    for j in range(num_copy):
                        idx += 1
                        fw.write(f"#pragma HLS INTERFACE mode = m_axi bundle = m{idx*4} port = A{idx}\n")
                        fw.write(f"#pragma HLS INTERFACE mode = m_axi bundle = m{idx*4+1} port = B{idx}\n")
                        fw.write(f"#pragma HLS INTERFACE mode = m_axi bundle = m{idx*4} port = C{idx}\n")
                        fw.write(f"#pragma HLS INTERFACE mode = m_axi bundle = m{idx*4+2} port = A_indice{idx}\n")
                        fw.write(f"#pragma HLS INTERFACE mode = m_axi bundle = m{idx*4+3} port = C_indice{idx}\n\n")
                        fw.write(f"  hls::stream<IDX_DTYPE> Aidx_stream{idx}(\"Aidx_stream{idx}\");\n")
                        fw.write(f"  hls::stream<IDX_DTYPE> Cidx_stream{idx}(\"Cidx_stream{idx}\");\n")
                        fw.write(f"  hls::stream<hls::vector<DTYPE, DSIZE>> Bstream{idx}(\"Bstream{idx}\");\n")
                        fw.write(f"  hls::stream<hls::vector<DTYPE, DSIZE>> Cstream{idx}(\"Cstream{idx}\");\n")
                        fw.write(f"  hls::stream<DTYPE> Astream{idx}(\"Astream{idx}\");\n\n")

                        fw.write(f"  readAidx1<Tm{idx}, Tn{idx}, Tk{idx}, IDX_DSIZE{idx}>(A_indice{idx}, Aidx_stream{idx}, M{idx}, N{idx}, K{idx});\n")
                        fw.write(f"  readCidx1<Tm{idx}, Tn{idx}, IDX_DSIZE{idx}>(C_indice{idx}, Cidx_stream{idx}, M{idx}, N{idx});\n")
                        fw.write(f"  readA1<Tm{idx}, Tn{idx}, Tk{idx}>(A{idx}, Astream{idx}, Aidx_stream{idx}, M{idx}, N{idx}, K{idx});\n")
                        fw.write(f"  readB1<Tm{idx}, Tn{idx}, Tk{idx}>(B{idx}, Bstream{idx}, M{idx}, N{idx}, K{idx});\n")
                        fw.write(f"  matmul_compute1<Tm{idx}, Tn{idx}, Tk{idx}>(Astream{idx}, Bstream{idx}, Cstream{idx}, M{idx}, N{idx}, K{idx}, relu{idx});\n")
                        fw.write(f"  writeC1<Tm{idx}, Tn{idx}>(C{idx}, Cstream{idx}, Cidx_stream{idx}, M{idx}, N{idx});\n")


def run_hls(root_dir, impl_dir, hls_proj_dir):

    print(f"{impl_dir}/{hls_proj_dir}/sol/syn/report/csynth.rpt")
    if os.path.isfile(f"{impl_dir}/{hls_proj_dir}/sol/syn/report/csynth.rpt"):
        print("exist")
    else:
        os.chdir(impl_dir)
        os.environ["HLS_HEAD_DIR"] = impl_dir
        os.environ["HLS_HEAD_FILE"] = f"{impl_dir}/matmul_tile.h"
        os.environ["HLS_PROJ_DIR"] = hls_proj_dir
        os.environ["HLS_SRC_DIR"] = impl_dir
        subprocess.run(["vitis_hls", f"{root_dir}/IP/impl/hls_tile.tcl"])

def run_impl(impl_dir, hls_proj_dir):
    hls_impl_dir = f"{impl_dir}/{hls_proj_dir}/sol/impl/verilog" 
    subprocess.run(["cp", "/mnt/shared/home/weizuo/moe_dse/moe_model/run_impl.tcl", hls_impl_dir])
    os.chdir(hls_impl_dir)
    subprocess.run(["vivado", "-mode", "tcl", "-source", "./run_impl.tcl"])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-ilp_sol', type=str, required=True)
    parser.add_argument('-ip_capacity', type=int, required = True)
    parser.add_argument('-build_dir', type=str, required=True)
    args = parser.parse_args()
    build_dir = args.build_dir
    
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    selected_ips = dict()
    ip_candidates_file = f"{build_dir}/ip_candidates.capacity{args.ip_capacity}.prune.log" #TODO
    generate_selected_ips(args.ilp_sol, ip_candidates_file, selected_ips, None)
    ip_candidates = generate_IP_list(ip_candidates_file)
    
    impl_dir = f"{build_dir}/impl_fp32_capacity{args.ip_capacity}"
    hls_proj_dir = f"matmul_hls_tile_impl_5ns"
    
    if not os.path.exists(impl_dir):
        os.makedirs(impl_dir)

    generate_files(root_dir, impl_dir, hls_proj_dir)
    run_hls(root_dir, impl_dir, hls_proj_dir)
    run_impl(impl_dir, hls_proj_dir) 

