import os

from utils.run_helper import *

def run(configs, workload, outdir):
    # @configs: {
    #   'arch_config_file': str<gem5_config_file>, 
    #   'arch_config_list': list<gem5_config_list>, 
    #   '3Dmem_config_file': str<3dmem_config_file>,
    #   'hotspot_inputs_dir': str<hotspot_inputs_dir>,
    #   'is_core_list': str<is_core_list>,
    #   'banks_per_layer': str<banks_per_layer>
    #   'microfluidic_cooling': bool<microfluidic_cooling>
    #   ...}
    # @workload: str, path to workload executable
    # @outdir: str, path to output directory

    gem5_outdir = os.path.join(outdir, 'perf')
    gen_performance_trace(
        configs['arch_config_file'], 
        configs['arch_config_list'], 
        workload, 
        gem5_outdir
    )

    mcpat_outdir = os.path.join(outdir, 'power')
    gen_core_power_trace(
        gem5_outdir, 
        mcpat_outdir
    )

    cacti_outdir = os.path.join(outdir, 'power')
    gen_mem_power_trace(
        configs['3dmem_config_file'], 
        gem5_outdir, 
        cacti_outdir
    )

    hotspot_outdir = os.path.join(outdir, 'thermal')
    gen_temperature_trace(
        mcpat_outdir=mcpat_outdir, 
        cacti_outdir=cacti_outdir,
        inputs_dir=configs['hotspot_inputs_dir'],
        is_core_list=configs['is_core_list'],
        banks_per_layer=configs['banks_per_layer'],
        hotspot_outdir=hotspot_outdir, 
        microfluidic_cooling=configs['microfluidic_cooling'] 
    )

    visualize(
        hotspot_outdir=hotspot_outdir,
        hotspot_inputs_dir=configs['hotspot_inputs_dir'],
        num_layers=configs['num_layers_total'],
        resolution=configs['sim_resolution']
    )