# Cool-3D Framework

[toc]

## Dependency
Install all the dependencies listed in [gem5-dependencies](https://www.gem5.org/documentation/general_docs/building) will be enough for Cool-3D

## Quick Start

1. Clone this repo and all the submodules
   ```shell
   git clone --recurse-submodules https://github.com/iCAS-SJTU/Cool-3D.git
   ```

2. Setup environment variables
   ```shell
   source setenv.sh
   ```
   Notice that every time you start a new terminal you will need to rerun this command. You can also add the commands in ``setenv.sh`` to your shell configuration file to save this effort. 

3. Build all the simulators
   ```shell
   source build.sh
   ```

## How to cite

If you use this code, please cite:

Wang, R., Wang, Z., Lin, T., Raby, J. M., Stan, M. R., & Guo, X. (2025). Cool-3D: An End-to-End Thermal-Aware Framework for Early-Phase Design Space Exploration of Microfluidic-Cooled 3DICs. arXiv preprint arXiv:2503.07297.

      @article{wang2025cool,
         title={Cool-3D: An End-to-End Thermal-Aware Framework for Early-Phase Design Space Exploration of Microfluidic-Cooled 3DICs},
         author={Wang, Runxi and Wang, Ziheng and Lin, Ting and Raby, Jacob M and Stan, Mircea R and Guo, Xinfei},
         journal={arXiv preprint arXiv:2503.07297},
         year={2025}
      }
