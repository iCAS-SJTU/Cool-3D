import argparse

argparser = argparse.ArgumentParser()
argparser.add_argument('--core-ptrace', type=str, help='core ptrace file')
argparser.add_argument('--mem-ptrace', type=str, help='mem ptrace file')
argparser.add_argument('--is-core', type=str, help='is core layer for each layer')
argparser.add_argument('--banks-per-layer', type=int, help='number of banks per memory layer')
argparser.add_argument('--coremem-ptrace', type=str, help='output combined ptrace file')

def read_core_ptrace(core_ptrace_file):
    core_ptrace_header = []
    core_ptrace_data = []

    with open(core_ptrace_file, 'r') as f:
        for line in f:
            if line.startswith('Warning'):
                continue
            for header in line.strip().split():
                core_ptrace_header.append(header)
            line = f.readline()
            for data in line.strip().split():
                core_ptrace_data.append(data)
            break

    return core_ptrace_header, core_ptrace_data

def read_mem_ptrace(mem_ptrace_file):
    mem_ptrace_header = []
    mem_ptrace_data = []

    with open(mem_ptrace_file, 'r') as f:
        line = f.readline()
        for header in line.strip().split():
            mem_ptrace_header.append(header)
        line = f.readline()
        for data in line.strip().split():
            mem_ptrace_data.append(data)

    return mem_ptrace_header, mem_ptrace_data

def combine_ptrace(core_ptrace_file, mem_ptrace_file, is_core, banks_per_layer, output_file):

    num_layers = len(is_core)
    core_ptrace_header, core_ptrace_data = read_core_ptrace(core_ptrace_file)
    mem_ptrace_header, mem_ptrace_data = read_mem_ptrace(mem_ptrace_file)
    mems_cnt = 0
    with open(output_file, 'w') as f:
        for i in range(num_layers):
            if is_core[i] == '1':
                f.write('\t'.join(core_ptrace_header) + '\t')
            else:
                f.write('\t'.join(mem_ptrace_header[mems_cnt * banks_per_layer : (mems_cnt+1) * banks_per_layer]) + '\t')
                mems_cnt += 1
        f.write('\n')
        mems_cnt = 0
        for i in range(num_layers):
            if is_core[i] == '1':
                f.write('\t'.join(core_ptrace_data) + '\t')
            else:
                f.write('\t'.join(mem_ptrace_data[mems_cnt * banks_per_layer : (mems_cnt+1) * banks_per_layer]) + '\t')
                mems_cnt += 1
        f.write('\n')
                
        # f.write('\t'.join(core_ptrace_header) + '\t' + '\t'.join(mem_ptrace_header) + '\n')
        # f.write('\t'.join(core_ptrace_data) + '\t' + '\t'.join(mem_ptrace_data) + '\n')

args = argparser.parse_args()

combine_ptrace(args.core_ptrace, args.mem_ptrace, args.is_core, args.banks_per_layer, args.coremem_ptrace)