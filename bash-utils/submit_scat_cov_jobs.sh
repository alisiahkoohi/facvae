#!/bin/bash -l

set -e

# 2**14 = 16384
scat_cov_filename="scat_covs_w-size-2e11_q1-2_q2-4_day-data-0_power-spectrum-0.h5"
python scripts/generate_scattering_cov.py --window_size 2048 --q1 2 \
    --q2 4  --use_day_data 0 --use_power_spectrum 0 \
    --scat_cov_filename $scat_cov_filename --cuda 1

# python scripts/insert_catalog_to_h5.py --h5_filename $scat_cov_filename --window_size 2048 > insert_scat_covs_w-size-2e11_q1-2_q2-4_day-data-0_power-spectrum-0.txt
