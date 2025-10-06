# Cool-3D Framework

[What is Cool-3D](#what-is-cool-3d)<br>
[Quick Start](#quick-start)<br>
[Tutorials](#tutorials)<br>
[How to Cite](#how-to-cite)

## What is Cool-3D

Cool-3D is an end-to-end thermal-aware framework built for early-phase design space exploration (DSE) of microfluidic cooling equipped 3DICs. It is built on top of mainstream computer architecture simulators gem5, McPAT, CACTI, and HotSpot.
Given architectural, stacking, thermal related information as inputs, this framework will efficiently output thermal traces with visualization results.

## Quick Start

### Dependency

1. Install all the dependencies listed in [gem5 dependencies](https://www.gem5.org/documentation/general_docs/building)
2. Install the 32-bit C++ multilib toolchain (required for compiling McPAT in 32-bit mode on 64-bit systems):
   ```shell
   apt install g++-multilib
   ```
3. Install SuperLU library for quick HotSpot steady simulation by
   ```shell
   apt-get install libsuperlu-dev
   ```
4. Install python packages

   Using pip:
   ```shell
   pip install -r requirements.txt
   ```
   Or using uv (faster alternative):
   ```shell
   uv venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   ```
   > if users choose the uv method, they'll need to remember to activate the virtual environment (`.venv/bin/activate`) every time they open a new terminal

### Tool Building

1. Clone this repo and all the submodules
   ```shell
   git clone --recurse-submodules https://github.com/iCAS-SJTU/Cool-3D.git
   ```

2. Setup environment variables
   ```shell
   cd Cool-3D
   source setenv.sh
   ```
   Notice that every time you start a new terminal you will need to rerun this command. You can also add the commands in ``setenv.sh`` to your shell configuration file to save this effort.

3. Build all the simulators
   ```shell
   ./build.sh
   ```
   By default, the script auto-detects available CPU cores. You can optionally specify the number of cores to use:
   ```shell
   ./build.sh <num_cores>
   ```

### Run an Example

If you have [Splash2 benchmark](https://github.com/liuyix/splash2_benchmark) downloaded and compiled in your host, you can run
```shell
python3 scripts/run_design.py --input-file=examples/example_0/inputs.yaml
```

If not, you can simply run a hello-world program to test whether Cool-3D is build successfully
```shell
python3 scripts/run_design.py --input-file=examples/example_0/inputs-hello.yaml
```


## Tutorials

Coming Soon:)

## Reporting Bugs
Please use our dedicated template to file bug reports. This helps us diagnose issues faster.

## How to cite

If you use this code, please cite:

R. Wang, Z. Wang, T. Lin, J. M. Raby, M. R. Stan and X. Guo, "Cool-3D: An End-to-End Thermal-Aware Framework for Early-Phase Design Space Exploration of Microfluidic-Cooled 3DICs," in IEEE Journal on Emerging and Selected Topics in Circuits and Systems, doi: 10.1109/JETCAS.2025.3590065. (https://ieeexplore.ieee.org/document/11083607)

      @ARTICLE{11083607,
        author={Wang, Runxi and Wang, Ziheng and Lin, Ting and Raby, Jacob M. and Stan, Mircea R. and Guo, Xinfei},
        journal={IEEE Journal on Emerging and Selected Topics in Circuits and Systems},
        title={Cool-3D: An End-to-End Thermal-Aware Framework for Early-Phase Design Space Exploration of Microfluidic-Cooled 3DICs},
        year={2025},
        volume={},
        number={},
        pages={1-1},
        keywords={Cooling;Stacking;Space exploration;Microfluidics;Through-silicon vias;Three-dimensional displays;Space cooling;Predictive models;Heat transfer;Computer architecture;3DIC;Design Space Exploration (DSE);Pre-RTL Design;Thermal Simulation;Microfluidic Cooling},
        doi={10.1109/JETCAS.2025.3590065}}

