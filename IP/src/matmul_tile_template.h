#pragma once
#include "hls_stream.h"
#include <algorithm>
#include <hls_vector.h>
// BEGIN DEFINE
// END
const int E = 1;
const int N_TKNS = 768;
const int D_MODEL = 768;
const int N_LAYER = 1;
typedef float DTYPE;
typedef short IDX_DTYPE;
const int DSIZE = 64 / sizeof(DTYPE); // number of DTYPEs in 512b
const int IDX_DSIZE = (64 / sizeof(IDX_DTYPE) > Tm) ? Tm : 64 / sizeof(IDX_DTYPE);
static_assert(Tk % DSIZE == 0 && Tn % DSIZE == 0); //The column of B should be dividable by DSIZE
static_assert(N_TKNS % IDX_DSIZE == 0); //The column of idx should be devidably by IDX_DSIZE
//printf("Tm = %d, IDX_DSIZE =%d\n", Tm, IDX_DSIZE);
//static_assert(Tm % IDX_DSIZE == 0);
extern "C" {
void matmul_tile(DTYPE *A0, hls::vector<IDX_DTYPE, IDX_DSIZE> *A_indice0,
                 hls::vector<IDX_DTYPE, IDX_DSIZE> *C_indice0,
                 hls::vector<DTYPE, DSIZE> *Bin0, 
                 //hls::vector<DTYPE, DSIZE> *Bout0, 
                 hls::vector<DTYPE, DSIZE> *C0, int M0, int N0, int K0, bool relu);
}
