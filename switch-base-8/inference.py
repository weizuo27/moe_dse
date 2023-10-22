# example command : python inference --split validation

from transformers import AutoTokenizer, SwitchTransformersForConditionalGeneration, SwitchTransformersEncoderModel
from datasets import load_dataset
from t5_data_collator import DataCollatorForT5MLM, compute_t5_input_and_target_lengths
import argparse

input_length = 100
mlm_probability = 0.1
mean_noise_span_length = 2
#batch_size = 1
parser = argparse.ArgumentParser()

parser.add_argument('--split', type=str) #choose between 'train' and 'validation'
parser.add_argument('--collect_time', type=bool) #True when the script is used to collect CPU runtime of validation run
args = parser.parse_args()
if args.collect_time:
    assert args.split="validataion"
    repeat = 100
else
    repeat = 1

for r in range(repeat):
    print("repeat", r)
    tokenizer = AutoTokenizer.from_pretrained("google/switch-base-8")
    model = SwitchTransformersEncoderModel.from_pretrained("google/switch-base-8")
    dataset = load_dataset('wikitext', 'wikitext-103-v1', split=args.split)
    batch_size = 8
        
    expanded_inputs_length, target_length = compute_t5_input_and_target_lengths(
            inputs_length=input_length,
            noise_density=mlm_probability,
            mean_noise_span_length=mean_noise_span_length,)
    
    data_collator = DataCollatorForT5MLM(
            tokenizer=tokenizer,
            noise_density=mlm_probability,
            mean_noise_span_length=mean_noise_span_length,
            input_length=input_length,
            target_length=target_length,
            pad_token_id=model.config.pad_token_id,
            decoder_start_token_id=model.config.decoder_start_token_id,
            )
    
    total_batch = tokenizer(dataset["text"], return_tensors="pt", padding=True, truncation=True, max_length=input_length)
    data_collator(total_batch) #create and fill mask
    total_batch_size = len(total_batch['input_ids'])
    
    #iterate through the batches to generate output
    for i in range(0, total_batch_size, batch_size):
        import sys; sys.stdout.flush();
        print("batch ", i, total_batch_size)
        batch_size_end = i+batch_size if i+batch_size<=total_batch_size else total_batch_size
        batch = total_batch['input_ids'][i:batch_size_end]
        output = model(batch)

