#include "matmul_tile.h"

template <int Tm, int Tn, int Tk>
static void readB1(hls::vector<DTYPE, DSIZE> *B,
                   hls::stream<hls::vector<DTYPE, DSIZE>> &Bstream, int M,
                   int N, int K) {
loop1:
  for (int ib = 0; ib < (M - 1) / Tm + 1; ib++) {
  loop2:
    for (int jb = 0; jb < (N - 1) / Tn + 1; jb++) {
    loop3:
      for (int kb = 0; kb < (K - 1) / Tk + 1; kb++) {
      loop4:
        for (int k = 0; k < Tk; k++) {
        loop5:
          for (int jj = 0; jj < Tn / DSIZE; jj++) {
#pragma HLS pipeline II = 1
            hls::vector<DTYPE, DSIZE> Bval =
                (kb * Tk + k >= K || jb * Tn + jj * DSIZE >= N)
                    ? hls::vector<DTYPE, DSIZE>(0.0f)
                    : B[((kb * Tk + k) * N + jb * Tn) / DSIZE + jj];
            Bstream << Bval;
          }
        }
      }
    }
  }
}

template <int Tm, int Tn>
static void writeC1(hls::vector<DTYPE, DSIZE> *C,
                    hls::stream<hls::vector<DTYPE, DSIZE>> &Cstream,
                    hls::stream<IDX_DTYPE> &Cidx_stream, int M, int N) {
  hls::vector<DTYPE, DSIZE> dummy;
loop1:
  for (int ib = 0; ib < (M - 1) / Tm + 1; ib++) {
  loop2:
    for (int jb = 0; jb < (N - 1) / Tn + 1; jb++) {
    loop3:
      for (int i = 0; i < Tm; ++i) {
        int row_idx = Cidx_stream.read();
      loop4:
        for (int jj = 0; jj < Tn / DSIZE; jj++) {
#pragma HLS pipeline II = 1
          //hls::vector<DTYPE, DSIZE> &out =
          //    (ib * Tm + i >= M  || jb * Tn+jj*DSIZE >=N) ? dummy
          //                     : C[(row_idx * N + jb * Tn) / DSIZE + jj];
          //out = Cstream.read();
	  if(not (ib * Tm + i >= M  || jb * Tn+jj*DSIZE >=N)){
	        C[(row_idx * N + jb * Tn) / DSIZE + jj] = Cstream.read();
	  } else {
	          dummy = Cstream.read();
	  }
        }
      }
    }
  }
}

template <int Tm, int Tn, int IDX_DSIZE>
static void readCidx1(hls::vector<IDX_DTYPE, IDX_DSIZE> *C_indice,
                      hls::stream<IDX_DTYPE> &Cidx_stream, int M, int N) {
loop1:
  for (int ib = 0; ib < (M - 1) / Tm + 1; ib++) {
  loop2:
    for (int jb = 0; jb < (N - 1) / Tn + 1; jb++) {
    loop3:
#pragma HLS pipeline II = 1
      for (int ii = 0; ii < (Tm - 1) / IDX_DSIZE + 1; ++ii) {
        hls::vector<IDX_DTYPE, IDX_DSIZE> Ctmp =
            C_indice[(ib * Tm) / IDX_DSIZE + ii];
      loop4:
        for (int i = 0;
             i < ((IDX_DSIZE > Tm - ii * IDX_DSIZE) ? Tm - ii * IDX_DSIZE
                                                    : IDX_DSIZE);
             ++i) {
          Cidx_stream << Ctmp[i];
        }
      }
    }
  }
}

template <int Tm, int Tn, int Tk, int IDX_DSIZE>
static void readAidx1(hls::vector<IDX_DTYPE, IDX_DSIZE> *A_indice,
                      hls::stream<IDX_DTYPE> &Aidx_stream, int M, int N,
                      int K) {
loop1:
  for (int ib = 0; ib < (M - 1) / Tm + 1; ib++) {
  loop2:
    for (int jb = 0; jb < (N - 1) / Tn + 1; jb++) {
    loop3:
      for (int kb = 0; kb < (K - 1) / Tk + 1; kb++) {
      loop4:
        for (int k = 0; k < Tk; k++) {
        loop5:
          for (int ii = 0; ii < (Tm - 1) / IDX_DSIZE + 1; ++ii) {
            // It is okay to read more than M here, as readA guards no reading
            // data more than M
#pragma HLS pipeline II = 1
            hls::vector<IDX_DTYPE, IDX_DSIZE> Atmp =
                A_indice[(ib * Tm) / IDX_DSIZE + ii];
          loop6:
            for (int i = 0; i < IDX_DSIZE; ++i){
		if(IDX_DSIZE * ii +i < Tm) Aidx_stream << Atmp[i];
            }
          }
        }
      }
    }
  }
}

template <int Tm, int Tn, int Tk>
static void readA1(DTYPE *A, hls::stream<DTYPE> &Astream,
                   hls::stream<IDX_DTYPE> &Aidx_stream, int M, int N, int K) {
loop1:
  for (int ib = 0; ib < (M - 1) / Tm + 1; ib++) {
  loop2:
    for (int jb = 0; jb < (N - 1) / Tn + 1; jb++) {
    loop3:
      for (int kb = 0; kb < (K - 1) / Tk + 1; kb++) {
      loop4:
        for (int k = 0; k < Tk; k++) {
        loop5:
          for (int i = 0; i < Tm; i++) {
#pragma HLS pipeline II = 1
            IDX_DTYPE row_idx = Aidx_stream.read();
            DTYPE Aval = (ib * Tm + i >= M || kb * Tk + k >= K)
                             ? 0.0f
                             : A[row_idx * K + kb * Tk + k];
            Astream << Aval;
          }
        }
      }
    }
  }
}

template <int Tm, int Tn, int Tk>
void matmul_compute1(
    hls::stream<DTYPE> &Astream,
    hls::stream<hls::vector<DTYPE, DSIZE>> &Bstream,
    hls::stream<hls::vector<DTYPE, DSIZE>> &Cstream, int M, int N, int K,
    bool relu) { // To pass co-sim: C has to be instantiated as array
  DTYPE C_block[Tm][Tn];
  DTYPE B_line[Tn];
#pragma HLS bind_storage variable=C_block type=RAM_S2P impl=bram
#pragma HLS ARRAY_PARTITION dim = 2 type = complete variable = C_block
#pragma HLS ARRAY_PARTITION dim = 1 type = complete variable = B_line
loop1:
  for (int ib = 0; ib < (M - 1) / Tm + 1; ib++) {
  loop2:
    for (int jb = 0; jb < (N - 1) / Tn + 1; jb++) {
      // initialize AB_block
    loop3:
      for (int i = 0; i < Tm; ++i) {
#pragma HLS pipeline II = 1
      loop4:
        for (int j = 0; j < Tn; ++j) {
#pragma HLS unroll
          C_block[i][j] = 0.0;
        }
      }
    loop5:
      for (int kb = 0; kb < (K - 1) / Tk + 1;
           kb++) { // TODO: Can 5, 6, 7 be flattern
      loop6:
        for (int k = 0; k < Tk; k++) {
        loop7:
          for (int jj = 0; jj < Tn / DSIZE; jj++) {
#pragma HLS pipeline II = 1
            hls::vector<DTYPE, DSIZE> B_tmp = Bstream.read();
          loop8:
            for (int j = 0; j < DSIZE; j++) {
#pragma HLS unroll
              B_line[jj * DSIZE + j] = B_tmp[j];
            }
          }
        loop9:
          for (int i = 0; i < Tm; i++) {
#pragma HLS pipeline II = 1
            DTYPE Atmp = Astream.read();
          loop10:
            for (int j = 0; j < Tn; ++j) {
#pragma HLS unroll
              C_block[i][j] = C_block[i][j] + Atmp * B_line[j];
            }
          }
        }
      }
      // Copy C_block to DRAM port C
    loop11:
      for (int i = 0; i < Tm; ++i) {
      loop12:
        for (int jj = 0; jj < Tn / DSIZE; jj++) {
#pragma HLS pipeline II = 1 // #TODO: What if I move II up a level
          hls::vector<DTYPE, DSIZE> C_tmp;
        loop13:
          for (int j = 0; j < DSIZE; ++j) {
#pragma HLS unroll
            C_tmp[j] = (relu && (C_block[i][jj*DSIZE + j] < 0.0f)) ? 0.0f : C_block[i][jj*DSIZE+j];
          }
          Cstream << C_tmp;
        }
      }
    }
  }
}

extern "C" {
void matmul_tile(
//BEGIN DEFINE0
//END
		 )

{ // To pass co-sim: C has to be instantiated as array

#pragma HLS DATAFLOW
//BEGIN DEFINE1
//END
}
}
