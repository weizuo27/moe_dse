#include "matmul_tile.h"
#include <fstream>
#include <iostream>
#include <random>
#include <stdio.h>
#include <vector>

template <typename T>
void readTensor(std::string file_name, int vec_size_per_read, T *vec,
                bool is_weight) {
  if (is_weight) {
    for (int i = 0; i < E * vec_size_per_read; i += vec_size_per_read) {
      std::string file_name_tmp =
          file_name + (std::to_string(i / vec_size_per_read) + ".pt.dat");
      std::cout << "file name " << file_name_tmp << std::endl;
      std::ifstream is(file_name_tmp);
      if (!is.is_open()) {
        std::cout << "cant open " << file_name_tmp << std::endl;
        return;
      }
      is.read(reinterpret_cast<char *>(&vec[i]), vec_size_per_read * sizeof(T));
      is.close();
    }
  } else {
    std::cout << "file name " << file_name << std::endl;
    std::ifstream is(file_name);
    if (!is.is_open()) {
      std::cout << "cant open " << file_name << std::endl;
      return;
    }
    is.read(reinterpret_cast<char *>(vec), vec_size_per_read * sizeof(T));
    is.close();
  }
}

template <typename T> static bool AreEqual(T f1, T f2) {
  return (std::fabs(f1 - f2) <= 1e-3);
  // std::numeric_limits<T>::epsilon() **
  // std::fmax(std::fabs(f1), std::fabs(f2)));
}

int main() {
  const int N = TCn * Tn;
  const int K = TCk * Tk;
  DTYPE *A = new DTYPE[N_TKNS * K];
  DTYPE *C_gold = new DTYPE[N_TKNS * K];

  IDX_DTYPE *Marr = new IDX_DTYPE[N_LAYER * E];

  DTYPE *B_in = new DTYPE[E * N * K];
  DTYPE *B_out = new DTYPE[E * N * K];

  hls::vector<DTYPE, DSIZE> *C =
      new hls::vector<DTYPE, DSIZE>[N_TKNS * N / DSIZE];

  IDX_DTYPE *A_idx = new IDX_DTYPE[E * N_TKNS];

  readTensor("/mnt/shared/home/weizuo/moe_dse/switch-base-8/tensors/"
             "hidden_state_layer1_bs8.pt.dat",
             N_TKNS * K, A, false);
  readTensor("/mnt/shared/home/weizuo/moe_dse/switch-base-8/tensors/"
             "next_state_layer1_bs8.pt.dat",
             N_TKNS * K, C_gold, false);
  readTensor(
      "/mnt/shared/home/weizuo/moe_dse/switch-base-8/tensors/wi_layer1_exp",
      N * K, B_in, true);

  readTensor(
      "/mnt/shared/home/weizuo/moe_dse/switch-base-8/tensors/wo_layer1_exp",
      N * K, B_out, true);

  readTensor("/mnt/shared/home/weizuo/moe_dse/switch-base-8/tensors/"
             "router_mask_layer1_bs8.pt.dat",
             E * N_TKNS, A_idx, false);

  for (int e = 0; e < E; ++e) {
    IDX_DTYPE n_tkn = 0;
    for (int i = 0; i < N_TKNS; ++i) {
      IDX_DTYPE idx = A_idx[e * N_TKNS + i];
      if (idx < 0)
        break;
      n_tkn += 1;
    }
    Marr[e] = n_tkn;
  }

  static_assert(N % Tn == 0 & K % Tk == 0);

  for (int e = 0; e < E; ++e) {
    matmul_tile(
        A,
        reinterpret_cast<hls::vector<IDX_DTYPE, IDX_DSIZE> *>(
            &A_idx[e * N_TKNS]),
        reinterpret_cast<hls::vector<IDX_DTYPE, IDX_DSIZE> *>(
            &A_idx[e * N_TKNS]),
        reinterpret_cast<hls::vector<DTYPE, DSIZE> *>(&B_in[e * N * K]),
        // reinterpret_cast<hls::vector<DTYPE, DSIZE> *>(&B_out[e * N * K]),
        C, Marr[e], N, K, true);
    matmul_tile(
        reinterpret_cast<DTYPE *>(C),
        reinterpret_cast<hls::vector<IDX_DTYPE, IDX_DSIZE> *>(
            &A_idx[e * N_TKNS]),
        reinterpret_cast<hls::vector<IDX_DTYPE, IDX_DSIZE> *>(
            &A_idx[e * N_TKNS]),
        reinterpret_cast<hls::vector<DTYPE, DSIZE> *>(&B_out[e * N * K]),
        reinterpret_cast<hls::vector<DTYPE, DSIZE> *>(A),
        Marr[e], K, N, false);
  }

  delete[] C;
  delete[] B_in;
  delete[] B_out;
  for (int e = 0; e < E; ++e) {
    for (int i = 0; i < Marr[e]; ++i) {
      IDX_DTYPE idx = A_idx[e * N_TKNS + i];
      assert(idx < N_TKNS);
      for (int j = 0; j < K; ++j) {
        assert(idx * K + j < N_TKNS * K);
        if (!AreEqual(C_gold[idx * K + j], A[idx * K + j])) {
          printf("ERROR! C_gold[%d][%d] = %f, C[%d][%d] = %f\n", idx, j,
                 C_gold[idx * K + j], idx, j, A[idx * K + j]);
          return 1;
        }
      }
    }
  }
  printf("\n\nSucceed!!!\n\n");
  delete[] A_idx;
  delete[] A;
  delete[] C_gold;
  delete[] Marr;
}
