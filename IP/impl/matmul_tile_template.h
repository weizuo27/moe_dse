#pragma once
#include "hls_stream.h"
#include <algorithm>
#include <hls_vector.h>

typedef float DTYPE;
typedef short IDX_DTYPE;
const int DSIZE = 64 / sizeof(DTYPE); // number of DTYPEs in 512b

// BEGIN DEFINE0
// END



extern "C" {
void matmul_tile(
// BEGIN DEFINE1
//END
		 );
}
