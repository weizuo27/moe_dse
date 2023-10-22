1. The benchmark is hugging face switch transformer base https://huggingface.co/google/switch-base-8. Install it on the test machine.

2. Replace the following file from the installed hugging face with the file with the same name in this directory.
	e.g., cp modeling_switch_transformers.py [python env path]/site-packages/transformers/models/switch_transformers/modeling_switch_transformers.py

3. uncomment "part 1, part 2, part 3" in the modeling\_switch\_transformers.py for different purposes. Refer to the comment in the file for detail.

1. To run inference to generate token distribution cross experts for DSE
	python inference.py  --split train --collect_time False 2>&1 |tee layer_log 
	python expert_analysis.py -fin ./layer_log -fout [build_dir]/experts_count.log

2. To run inference to generate token distribution cross experts for validation
	python inference.py --split validation  --collect_time False 2>&1 | tee validation_log
	python expert_analysis.py -fin ./validation_log -fout [build_dir]/validation_expert_count.log

3. To run inference to generate runtime of expert computation on 8 CPUs
	taskset --cpu-list 0-7 python inference.py --split validation --collect_time True 2>&2 | tee time_log
	python parse_time.py -input_file time_log 2>&1 | validation_time
