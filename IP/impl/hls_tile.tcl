open_project $env(HLS_PROJ_DIR)
set_top matmul_tile
add_files $env(HLS_HEAD_FILE)
add_files $env(HLS_SRC_DIR)/matmul_tile.cpp -cflags "-std=gnu++14 -I$env(HLS_HEAD_DIR)"
add_files -tb $env(HLS_SRC_DIR)/test_tile.cpp  
open_solution sol -flow_target vivado
set_part {xcvu13p-fsga2577-2LV-e}
create_clock -period 5 -name default
#csim_design
csynth_design
#cosim_design
export_design -format ip_catalog -flow syn
