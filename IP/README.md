The steps to generate IP candidates for DSE

cd script

1. Generate sampled IPs through HLS
	python generate_hls_runs.py  [arguments refer to the python file]
2. Generate csv file for metrics of sampled IPs
	python generate_ip_csv.py   [arguments refer to the python file]
3. Generate IP modeling based on sampled HLS IPs
	python fitting.py [arguments refer to the python file]
