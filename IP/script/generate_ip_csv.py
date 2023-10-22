import re
import argparse
import os

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-M', type=str, required=True) #M dim
    parser.add_argument('-N', type=str, required=True) #N dim
    parser.add_argument('-K', type=str, required=True) #K dim
    parser.add_argument('-build_dir', type=str, required=True) #The build directory in which HLS IPs are

    args = parser.parse_args()

    Ms = list(map(int, args.M.split(",")))
    Ns = list(map(int, args.N.split(",")))
    Ks = list(map(int, args.K.split(",")))

    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    build_dir = args.build_dir#f"{root_dir}/build"

    with open(f"{build_dir}/ip_csv.log", "w") as fw:
        for M, N, K in zip(Ms, Ns, Ks):
            #hls_dir = f"{build_dir}/hls/M{M}_N{N}_K{K}"
            hls_dir = f"{build_dir}"
            for f in [f for f in os.listdir(hls_dir) if "matmul_hls_tile" in f]:
                Tm, Tn, Tk =  re.match(r"matmul_hls_tile_Tm(\d+)Tn(\d+)Tk(\d+)", f).groups()
                csync_file = f"{hls_dir}/{f}/sol_Tm{Tm}_Tn{Tn}_Tk{Tk}/syn/report/csynth.rpt"
                if os.path.isfile(csync_file):
                    with open(csync_file, "r") as fr:
                        for line in fr:
                            if "|+ matmul_tile" in line:
                                data = line.split("|")
                                latency = int(data[4])
                                bram, dsp, ff, lut = data[10:14]
                                bram_num, bram_pct = re.findall("[0-9]+", bram)
                                dsp_num, dsp_pct = re.findall("[0-9]+", dsp)
                                ff_num, ff_pct = re.findall("[0-9]+", ff)
                                lut_num, lut_pct = re.findall("[0-9]+", lut)
                                bram_pct, dsp_pct, ff_pct, lut_pct = int(bram_pct), int(dsp_pct), int(ff_pct), int(lut_pct)
                                if (bram_pct > 100 or dsp_pct > 100 or ff_pct > 100 or lut_pct > 100):
                                    continue;
                                assert(max(dsp_pct, lut_pct) > bram_pct and max(dsp_pct, lut_pct) > ff_pct)
                                fw.write(f"{M}, {N}, {K}, {Tm}, {Tn}, {Tk}, {latency}, {dsp_num}, {lut_num}, {bram_num}, {ff_num}, {dsp_pct}, {lut_pct}, {bram_pct}, {ff_pct}\n")
