import argparse
import sys
import os

sys.path.append(os.environ['COOL3D_ROOT'])

import utils.run as run
import utils.parse_input as parse_input

argparser = argparse.ArgumentParser()
argparser.add_argument('--input-file', type=str, help='Input file in YAML format')

args = argparser.parse_args()

config, workload, outdir = parse_input.parse_input(args.input_file)

run.run(config, workload, outdir)