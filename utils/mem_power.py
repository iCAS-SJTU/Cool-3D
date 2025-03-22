import json
import re
import argparse

class mem_power:
  def __init__(self, config_file, stats_file, cacti_out, output_file):
    # read config data from gem5 config file
    F = open(config_file)
    gem5_config = json.load(F)
    self.num_bank = int(gem5_config['system']['mem_ctrls'][0]['dram']['banks_per_rank']) * int(gem5_config['system']['mem_ctrls'][0]['dram']['ranks_per_channel'])
    self.burst_length = int(gem5_config['system']['mem_ctrls'][0]['dram']['burst_length'])
    F.close()

    # initiate the access rates for each bank
    self.access_rates_rd = [0 for number in range(self.num_bank)]
    self.access_rates_wr = [0 for number in range(self.num_bank)]

    # read stats data from gem5 stats file
    F = open(stats_file)
    ignores = re.compile(r'^---|^$')
    gem5_stats = re.compile(r'([a-zA-Z0-9_\.:-]+)\s+([-+]?[0-9]+\.[0-9]+|[-+]?[0-9]+|nan|inf)')
    bank_idx_rd = 0
    bank_idx_wr = 0
    for line in F:
        if not ignores.match(line):
            # obtain the stats name and corresponding value
            try:
              stat_key = gem5_stats.match(line).group(1)
              stat_val = gem5_stats.match(line).group(2)
            except Exception as e:
              continue
            if 'perBankRdBursts' in stat_key:
              self.access_rates_rd[bank_idx_rd] = int(stat_val)
              bank_idx_rd += 1
            elif 'perBankWrBursts' in stat_key:
              self.access_rates_wr[bank_idx_wr] = int(stat_val)
              bank_idx_wr += 1
            elif 'simSeconds' in stat_key:
              self.sampling_interval = float(stat_val) * 1e9
            else:
              continue
    F.close()

    print(gem5_stats)
    self.mem_ptrace_file = output_file

    # read stats data from cacti output file
    with open(cacti_out) as f:
      line = f.readline()
      line = f.readline()
      self.energy_per_read_access = float(line.strip().split(',')[8]) * self.burst_length
      self.energy_per_write_access = float(line.strip().split(',')[9]) * self.burst_length
      self.leakage_per_bank = float(line.strip().split(',')[10]) 

  def gen_mem_ptrace_header(self):
    # return the header of the memory power trace file
    mem_ptrace_header = ''
    for bank_idx in range(self.num_bank):
      mem_ptrace_header = mem_ptrace_header + "B_" + str(bank_idx) + "\t" 
    
    return mem_ptrace_header

  def calc_access_power_trace(self):
    # calculate the access power and output the overall mem trace file
    bank_power_trace = [0 for number in range(self.num_bank)]
    #total power = access_count*energy per access + leakage power 
    #calculate bank power for each bank using access traces

    for bank in range(self.num_bank):
      bank_power_trace[bank] = (self.access_rates_rd[bank] * self.energy_per_read_access + self.access_rates_wr[bank] * self.energy_per_write_access) / self.sampling_interval + self.leakage_per_bank
      bank_power_trace[bank] = round(bank_power_trace[bank], 3)

    power_trace = ''

    for bank in range(len(bank_power_trace)):
        power_trace = power_trace + str(bank_power_trace[bank]) + '\t'

    mem_ptrace_header = self.gen_mem_ptrace_header()
    with open("%s" %(self.mem_ptrace_file), "w") as f:
        f.write("%s\n" %(mem_ptrace_header))
        f.write("%s" %(power_trace))
    f.close()

parser = argparse.ArgumentParser(description='Generate memory power trace')

parser.add_argument('--gem5-config', type=str, help='gem5 output config.json file')
parser.add_argument('--gem5-stats', type=str, help='gem5 output stats.txt file')
parser.add_argument('--cacti-out', type=str, help='cacti output file')
parser.add_argument('--output-file', type=str, help='output filename of generated mem power trace file', default='mem_power_trace.txt')

args = parser.parse_args()
config_file = args.gem5_config
stats_file = args.gem5_stats
cacti_out = args.cacti_out
output_file = args.output_file
mem_power_0 = mem_power(config_file, stats_file, cacti_out, output_file)
mem_power_0.calc_access_power_trace()