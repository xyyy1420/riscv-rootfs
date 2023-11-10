#!/bin/sh
echo '===== Start running SPEC2006 ====='
echo '======== BEGIN mcf ========'
set -x
md5sum /spec/astar_base.riscv64-linux-gnu-gcc12.2.0
date -R
cd /spec && ./astar_base.riscv64-linux-gnu-gcc12.2.0 BigLakes2048.cfg
date -R
set +x
echo '======== END   mcf ========'
echo '===== Finish running SPEC2006 ====='
