import argparse
def sort_key(a):
    return -a
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-input_file", type=str, required = True)

    args = parser.parse_args()
    dur_times = list()
    dur_time_per_repeat = 0.0
    with open (args.input_file, 'r') as f:
        for line in f:
            if "repeat" in line:
                dur_times.append(dur_time_per_repeat)
                dur_time_per_repeat = 0
            if "dur_time" in line:
                dur_time_per_repeat += float(line.split()[-1])


    print(dur_times, len(dur_times))
    assert(dur_times[0] == 0.0)
    dur_times = sorted(dur_times, key=sort_key)
    dur_times = dur_times[1:30]
    print("\n\n", dur_times, len(dur_times))
    mean_time =sum(dur_times)/(len(dur_times))
    print("meantime", mean_time)
