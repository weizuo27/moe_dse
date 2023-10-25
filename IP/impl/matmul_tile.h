#pragma once
#include "hls_stream.h"
#include <algorithm>
#include <hls_vector.h>

typedef float DTYPE;
typedef short IDX_DTYPE;
const int DSIZE = 64 / sizeof(DTYPE); // number of DTYPEs in 512b

// BEGIN DEFINE0
const int Tm0 = 8;
const int Tn0 = 256;
const int Tk0 = 256;
const int IDX_DSIZE0 = (64 / sizeof(IDX_DTYPE) > Tm0) ? Tm0 : 64 / sizeof(IDX_DTYPE);
static_assert(Tk0 % DSIZE == 0 && Tn0 % DSIZE == 0); //The column of B should be dividable by DSIZE

const int Tm1 = 8;
const int Tn1 = 256;
const int Tk1 = 256;
const int IDX_DSIZE1 = (64 / sizeof(IDX_DTYPE) > Tm1) ? Tm1 : 64 / sizeof(IDX_DTYPE);
static_assert(Tk1 % DSIZE == 0 && Tn1 % DSIZE == 0); //The column of B should be dividable by DSIZE
// END



extern "C" {
void matmul_tile(
// BEGIN DEFINE1
		DTYPE *A0, hls::vector<IDX_DTYPE, IDX_DSIZE0> *A_indice0,
                 hls::vector<IDX_DTYPE, IDX_DSIZE0> *C_indice0,
                 hls::vector<DTYPE, DSIZE> *B0, hls::vector<DTYPE, DSIZE> *C0,
                 int M0, int N0, int K0,
                 bool relu0,

		DTYPE *A1, hls::vector<IDX_DTYPE, IDX_DSIZE1> *A_indice1,
                hls::vector<IDX_DTYPE, IDX_DSIZE1> *C_indice1,
                hls::vector<DTYPE, DSIZE> *B1, hls::vector<DTYPE, DSIZE> *C1,
                int M1, int N1, int K1,
                 bool relu1
//END
		 );
}
