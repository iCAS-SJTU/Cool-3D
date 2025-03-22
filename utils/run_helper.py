import subprocess
import os
import glob

def gen_performance_trace(config_file, config_list, workload, outdir):
    # Run gem5 simulation and generate performance trace
    # @config_file: path to .py file for gem5 configuration
    # @config_list: list of configuration options based on the config file
    # @workload: path to the workload executable
    # @outdir: output directory for gem5 simulation

    gem5_root = os.environ['GEM5_ROOT']
    gem5_build = os.path.join(gem5_root, 'build')
    sim_exec = os.path.join(gem5_build, 'X86', 'gem5.opt')
    gem5_config = config_file
    if type(config_list) is str:
        configs = config_list.split()
        config_list = [config for config in configs]
    cmd = [sim_exec, "--outdir", outdir, gem5_config, "--cmd", workload] + config_list
    subprocess.run(cmd)
    print("[COOL-3D] Performance trace generated at ", outdir)

def gen_core_power_trace(gem5_outdir, outdir):
    # Run McPAT and generate core power trace
    # @gem5_outdir: path to the gem5 output directory
    # @outdir: output directory for McPAT simulation

    mcpat_root = os.environ['MCPAT_ROOT']
    utils_root = os.path.join(os.environ['COOL3D_ROOT'], 'utils')
    # parse gem5 output to generate McPAT input
    stats = os.path.join(gem5_outdir, 'stats.txt')
    config = os.path.join(gem5_outdir, 'config.json')
    template = os.path.join(utils_root, 'template_parser.xml')
    cmd = ['python3', os.path.join(utils_root, 'generate_template.py')]
    subprocess.run(cmd)
    cmd = ['python3', os.path.join(utils_root, 'gem52mcpat_parser.py'), '-c', config, '-s', stats, '-t', template]
    subprocess.run(cmd)
    cmd = ['mkdir', '-p', outdir]
    subprocess.run(cmd)
    cmd = ['mv', 'mcpat_in.xml', outdir]
    subprocess.run(cmd)
    print("[COOL-3D] McPAT input prepared at ", outdir)

    # run mcpat
    mcpat_exec = os.path.join(mcpat_root, 'mcpat')
    cmd = [mcpat_exec, '-infile', os.path.join(outdir, 'mcpat_in.xml'), '-print_level', '5', '-opt_for_clk', '1']
    subprocess.run(cmd)
    cmd = ['mv', 'out.ptrace', os.path.join(outdir, 'mcpat_out.ptrace')]
    subprocess.run(cmd)
    cmd = ['mv', 'out.area', os.path.join(outdir, 'mcpat_out.area')]
    subprocess.run(cmd)
    cmd = ['mv', 'out.area_hierarchy', os.path.join(outdir, 'mcpat_out.area_hierarchy')]
    subprocess.run(cmd)
    print("[COOL-3D] Core power trace generated at ", outdir)

def gen_mem_power_trace(cacti_in, gem5_output, cacti_outdir):
    # Run CACTI-3DD and generate memory power trace
    # @cacti_in: path to the CACTI-3DD input file
    # @gem5_output: path to the gem5 output directory
    # @cacti_outdir: output directory for CACTI-3DD simulation
    cacti_root = os.environ['CACTI_ROOT']
    utils_root = os.path.join(os.environ['COOL3D_ROOT'], 'utils')
    cmd = ['./cacti', '-infile', cacti_in]
    subprocess.run(cmd, cwd=cacti_root)
    cacti_out = cacti_in + ".out"
    cacti_out_temp_dir = os.path.join(os.path.dirname(cacti_in), cacti_out)
    cmd = ['mv', cacti_out_temp_dir, cacti_outdir]
    subprocess.run(cmd)
    cacti_out = os.path.join(cacti_outdir, os.path.basename(cacti_out))
    print("[COOL-3D] CACTI-3DD output generated at ", cacti_outdir)

    stats = os.path.join(gem5_output, 'stats.txt')
    config = os.path.join(gem5_output, 'config.json')
    output = os.path.join(cacti_outdir, 'mem.ptrace')
    mem_power_calc = os.path.join(utils_root, 'mem_power.py')
    cmd = ['python3', mem_power_calc, '--gem5-config', config, '--gem5-stats', stats, '--cacti-out', cacti_out, '--output-file', output]
    subprocess.run(cmd)
    print("[COOL-3D] Memory power trace generated at ", cacti_outdir)

def gen_temperature_trace(mcpat_outdir, cacti_outdir, inputs_dir,is_core_list, banks_per_layer, hotspot_outdir, microfluidic_cooling=False):
    # Run HotSpot and generate temperature trace
    # @mcpat_outdir: path to the McPAT output directory
    # @cacti_outdir: path to the CACTI-3DD output directory
    # @inputs_dir: path to the input directory for HotSpot
    # @is_core_list: list of 0s and 1s to identify core and memory layers, e.g. '100' means the bottom layer is core and the rest are memory
    # @banks_per_layer: number of memory banks per memory bank layer
    # @hotspot_outdir: output directory for HotSpot simulation
    # @microfluidic_cooling: whether to enable microfluidic cooling
    hotspot_root = os.environ['HOTSPOT_ROOT']
    utils_root = os.path.join(os.environ['COOL3D_ROOT'], 'utils')
    # combine the ptraces for core and mem
    core_ptrace = os.path.join(mcpat_outdir, 'mcpat_out.ptrace')
    mem_ptrace = os.path.join(cacti_outdir, 'mem.ptrace')
    cmd = ['python3', os.path.join(utils_root, 'coremem_ptrace_combine.py'), '--core-ptrace', core_ptrace, '--mem-ptrace', mem_ptrace, '--coremem-ptrace', os.path.join(mcpat_outdir, 'coremem.ptrace'), '--is-core', is_core_list, '--banks-per-layer', banks_per_layer]
    subprocess.run(cmd)
    print("[COOL-3D] Core and memory ptraces combined at ", mcpat_outdir)

    # prepare hotspot inputs
    hotspot_running_dir = os.path.join(hotspot_root, 'cool_3d_thermal')
    cmd = ['rm', '-rf', hotspot_running_dir]
    subprocess.run(cmd)
    cmd = ['cp', inputs_dir, '-r', hotspot_running_dir]
    subprocess.run(cmd)
    # hotspot_running_dir = os.path.join(hotspot_root, os.path.basename(inputs_dir))
    config = glob.glob(os.path.join(hotspot_running_dir, '*.config'))[0]
    materials = glob.glob(os.path.join(hotspot_running_dir, '*.materials'))[0]
    stack = glob.glob(os.path.join(hotspot_running_dir, '*.lcf'))[0]
    ptrace = os.path.join(mcpat_outdir, 'coremem.ptrace')
    cmd = ['cp', ptrace, hotspot_running_dir]
    subprocess.run(cmd)
    print("[COOL-3D] Hotspot inputs copied to ", hotspot_root)
    
    # run hotspot
    cmd = ['rm', '-rf', 'outputs']
    subprocess.run(cmd, cwd=hotspot_running_dir)
    cmd = ['mkdir', '-p', 'outputs']
    subprocess.run(cmd, cwd=hotspot_running_dir)
    cmd = ['../hotspot', 
           '-p', 'coremem.ptrace', # need absolute path
           '-c', config, 
           '-materials_file', materials, 
           '-grid_layer_file', stack, 
           '-model_type', 'grid', 
           '-detailed_3D', 'on', 
           '-steady_file', 'outputs/coremem.steady',
           '-grid_steady_file', 'outputs/coremem.grid.steady']
    if microfluidic_cooling:
        cmd += ['-use_microchannels', '1']
    subprocess.run(cmd, cwd=hotspot_running_dir)
    print("[COOL-3D] Hotspot simulation done at ", hotspot_running_dir)

    # move the outputs to main output directory
    cmd = ['rm', '-rf', hotspot_outdir]
    subprocess.run(cmd)
    cmd = ['cp', 'outputs/', '-r', hotspot_outdir]
    subprocess.run(cmd, cwd=hotspot_running_dir)
    print("[COOL-3D] Hotspot outputs copied to ", hotspot_outdir)

def visualize(hotspot_outdir, hotspot_inputs_dir, num_layers, resolution):
    # @hotspot_outdir: path to the hotspot outputs
    # @num_layers: total number of layers in the 3D stack, including interposer and tim layers
    # @resolution: 2-element list, resolution of the hotspot grid in x and y directions

    hotspot_root = os.environ['HOTSPOT_ROOT']
    hotspot_scripts_dir = os.path.join(hotspot_root, 'scripts')
    steady_trace = os.path.join(hotspot_outdir, 'coremem.grid.steady')

    # split the traces for each layer
    split_helper = os.path.join(hotspot_scripts_dir, 'split_grid_steady.py')
    cmd = [split_helper, steady_trace, str(num_layers), str(resolution[0]), str(resolution[1])]
    subprocess.run(cmd, cwd=hotspot_outdir)
    print("[COOL-3D] Steady temperature trace split for each layer in ", hotspot_outdir)

    # match the layers to the floorplans
    stack_file = os.path.join(hotspot_inputs_dir, 'stack.lcf')
    floorplan_list = match_layer(stack_file)

    # visualize the temperature traces in the format of heat maps
    for i, floorplan in enumerate(floorplan_list):
        layer_name = os.path.basename(floorplan).split('.')[0]
        cmd = [
            'python3', 
            os.path.join(hotspot_scripts_dir, 'grid_thermal_map.py'), 
            os.path.join(hotspot_inputs_dir, floorplan),
            os.path.join(hotspot_outdir, 'coremem_layer'+str(i)+'.grid.steady'),
            str(resolution[0]), str(resolution[1]),
            os.path.join(hotspot_outdir, 'layer'+str(i)+'_'+layer_name+'.png')
        ]
        subprocess.run(cmd)
        print("[COOL-3D] Generating thermal map for layer ", i, " at ", os.path.join(hotspot_outdir, 'layer'+str(i)+layer_name+'.png'))

def match_layer(stack_file):
    # @stack_file: path to the stacking file
    # return: list of floorplan files for each layer in the stack

    floorplans = []
    with open(stack_file, 'r') as f:
        for line in f:
            if line.startswith('#') or line.startswith('\n'):
                continue
            else:
                layer_idx = line.strip()
                f.readline()
                f.readline()
                f.readline()
                f.readline()
                possible_floorplan = f.readline()
                floorplan = f.readline()

                if floorplan == '\n':
                    floorplan = possible_floorplan
                
                floorplans.append(floorplan.strip())
                print("[COOL-3D] Layer ", layer_idx, " has floorplan file at ", floorplan.strip())
    
    return floorplans