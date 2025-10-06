#!/bin/bash

# set -e  # Exit on error

# Default number of cores
NUM_CORES=${1:-$(nproc 2>/dev/null || echo 4)}

# if [ -z "$1" ]; then
#     NUM_CORES=4
# else
#     NUM_CORES=$1
# fi

echo "[COOL-3D] Cool-3D building with $NUM_CORES cores"

cd $MCPAT_ROOT
if [ ! -f mcpat ]; then
    echo "[COOL-3D] Building McPAT"
    make
else
    echo "[COOL-3D] MCPAT already built"
fi
cd $COOL3D_ROOT

cd $CACTI_ROOT
if [ ! -f cacti ]; then
    echo "[COOL-3D] Building CACTI"
    make
else
    echo "[COOL-3D] CACTI already built"
fi
cd $COOL3D_ROOT

cd $HOTSPOT_ROOT
if [ ! -f hotspot ]; then
    echo "[COOL-3D] Building HotSpot"
    make SUPERLU=1
else
    echo "[COOL-3D] HotSpot already built"
fi
cd $COOL3D_ROOT

cd $GEM5_ROOT
if [ ! -f build/X86/gem5.opt ]; then
    echo "[COOL-3D] Building gem5"
    scons build/X86/gem5.opt -j $NUM_CORES
else
    echo "[COOL-3D] gem5 already built"
fi

cd $COOL3D_ROOT
echo "[COOL-3D] Finished building"
