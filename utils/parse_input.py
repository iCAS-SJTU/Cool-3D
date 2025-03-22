import yaml
import os
import glob

def parse_input(input_file):
    # @input_file: str, path to the top level yaml input file

    with open(input_file, 'r') as stream:
        try:
            inputs=yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            exit(1)
    
    # check existence of required configuration options
    if not inputs.get("arch"):
        print("[COOL-3D] Error: Architecture configuration not found in ", input_file)
        exit(1)
    if not inputs.get("workload"):
        print("[COOL-3D] Error: Workload configuration not found in ", input_file)
        exit(1)
    if not inputs.get("thermal"):
        print("[COOL-3D] Error: Thermal configuration not found in ", input_file)
        exit(1)

    # workload configuration
    workload = inputs["workload"]
    if not workload.get("bin"):
        print("[COOL-3D] Error: Path to workload executable not found in ", input_file)
        exit(1)
    else:
        workload_bin = os.path.expandvars(workload["bin"])
    if not workload.get("opt"):
        workload_opt = ''
    else: 
        workload_opt = str(workload["opt"])
    if not workload.get("input"):
        workload_input = ''
    else:
        workload_input = str(workload["input"])

    config = {}

    arch = inputs["arch"]
    # required arch configuration files
    if not arch.get("arch_config_file"):
        print("[COOL-3D] Error: gem5 configuration file (.py) not found in ", input_file)
        exit(1)
    else:
        config["arch_config_file"] = os.path.expandvars(arch["arch_config_file"])
    if not arch.get("3Dmem_config_file"):
        print("[COOL-3D] Error: 3D memory configuration file (.cfg) not found in ", input_file)
        exit(1)
    else:
        config["3dmem_config_file"] = os.path.expandvars(arch["3Dmem_config_file"])

    # construct the gem5 configuration list
    arch_config_list = []
    if arch.get("num_cores"):
        arch_config_list.append('-n=' + str(arch["num_cores"]))
    else:
        arch_config_list.append('-n=4')
    if arch.get("cpu_clock"):
        arch_config_list.append('--cpu-clock=' + str(arch["cpu_clock"]))
    else:
        arch_config_list.append('--cpu-clock=2GHz')
    if arch.get("l2_size"):
        arch_config_list.append('--l2_size=' + str(arch["l2_size"]))
    else:
        arch_config_list.append('--l2_size=2MB')
    if arch.get("mem_size"):
        arch_config_list.append('--mem-size=' + str(arch["mem_size"]))
    else:
        arch_config_list.append('--mem-size=8GB')
    if arch.get("num_mem_banks"):
        arch_config_list.append('--mem-ranks=' + str(int(arch["num_mem_banks"]/8)))
    else:
        print("[COOL-3D] Error: Number of memory banks not found in ", input_file)
        exit(1)
    # more supported options are coming:)

    config["arch_config_list"] = arch_config_list + ['--cpu-type=X86O3CPU', '--caches', '--l2cache'] + ['--options=' + workload_opt] + ['--input=' + workload_input]

    # stacking configuration
    thermal = inputs["thermal"]
    if not thermal.get("hotspot_inputs_dir"):
        print("[COOL-3D] Error: Path to thermal simulation inputs directory not found in ", input_file)
        exit(1)
    else:
        config["hotspot_inputs_dir"] = os.path.expandvars(thermal["hotspot_inputs_dir"])

    if not thermal.get("num_layers_total"):
        print("[COOL-3D] Error: Number of total stacking layers not found in ", input_file)
        exit(1)
    else:
        config["num_layers_total"] = thermal["num_layers_total"]
    
    if not thermal.get("is_core"):
        print("[COOL-3D] Error: Core layer identification not found in ", input_file)
        exit(1)
    else:
        config["is_core_list"] = str(thermal["is_core"])
    
    if not thermal.get("banks_per_layer"):
        print("[COOL-3D] Error: Number of memory banks per layer not found in ", input_file)
        exit(1)
    else:
        config["banks_per_layer"] = str(thermal["banks_per_layer"])
    
    if thermal.get("microfluidic_cooling"):
        config["microfluidic_cooling"] = bool(thermal["microfluidic_cooling"])
    else:
        config["microfluidic_cooling"] = False
    
    if not glob.glob(os.path.join(config["hotspot_inputs_dir"], '*.lcf')):
        print("[COOL-3D] Error: Stacking configuration file (.lcf) not found in ", config["hotspot_inputs_dir"])
        exit(1)
    else:
        config["stack_config"] = glob.glob(os.path.join(config["hotspot_inputs_dir"], '*.lcf'))[0]

    if thermal.get("sim_resolution_row") and thermal.get("sim_resolution_col"):
        config["sim_resolution"] = [int(thermal["sim_resolution_row"]), int(thermal["sim_resolution_col"])]
    else:
        config["sim_resolution"] = [64, 64]

    print(config["sim_resolution"])

    # output directory
    if not inputs.get("outdir"):
        outdir = os.path.join(os.environ['COOL3D_ROOT'], 'outputs')
    else:
        outdir = inputs["outdir"]


    return config, workload_bin, outdir