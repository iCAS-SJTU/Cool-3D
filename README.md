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