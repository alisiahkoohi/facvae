# CUDA_VISIBLE_DEVICES=0 python scripts/train_gmvae.py --h5_filename 3c_window_size-2048_q-6-6-6_j-7-7-7_use_day_data-1_avg_pool-0_model_type-scat_filter_key-true.h5 --type scat_cov_pca_25 --experiment_name 666-66 --normalize 0 --latent_dim 32 --cuda 1 --ncluster 9 --filter_key '' --nlayer 4
CUDA_VISIBLE_DEVICES=0 python scripts/train_gmvae.py --h5_filename 3c_window_size-2048_q-6-6-6_j-7-7-7_use_day_data-1_avg_pool-0_model_type-scat_filter_key-true.h5 --type cov_pca_6-6_25 --experiment_name 666-66 --normalize 0 --latent_dim 32 --cuda 1 --ncluster 9 --filter_key '' --nlayer 4
CUDA_VISIBLE_DEVICES=0 python scripts/train_gmvae.py --h5_filename 3c_window_size-2048_q-6-6-6_j-7-7-7_use_day_data-1_avg_pool-0_model_type-scat_filter_key-true.h5 --type scat_cov_pca_75 --experiment_name 666-66 --normalize 0 --latent_dim 32 --cuda 1 --ncluster 9 --filter_key '' --nlayer 4
CUDA_VISIBLE_DEVICES=0 python scripts/train_gmvae.py --h5_filename 3c_window_size-2048_q-6-6-6_j-7-7-7_use_day_data-1_avg_pool-0_model_type-scat_filter_key-true.h5 --type scat_cov_pca_25,cov_pca_6-6_25 --experiment_name 666-66_all --normalize 0 --latent_dim 32 --cuda 1 --ncluster 9 --filter_key '' --nlayer 4
CUDA_VISIBLE_DEVICES=0 python scripts/train_gmvae.py --h5_filename 3c_window_size-2048_q-6-6-6_j-7-7-7_use_day_data-1_avg_pool-0_model_type-scat_filter_key-true.h5 --type scat_cov_pca_25,cov_pca_6-6_75 --experiment_name 666-66_all --normalize 0 --latent_dim 32 --cuda 1 --ncluster 9 --filter_key '' --nlayer 4
CUDA_VISIBLE_DEVICES=0 python scripts/train_gmvae.py --h5_filename 3c_window_size-2048_q-6-6-6_j-7-7-7_use_day_data-1_avg_pool-0_model_type-scat_filter_key-true.h5 --type scat_cov_pca_25,cov_pca_6-6 --experiment_name 666-66_all --normalize 0 --latent_dim 32 --cuda 1 --ncluster 9 --filter_key '' --nlayer 4

CUDA_VISIBLE_DEVICES=0 python scripts/train_gmvae.py --h5_filename 3c_window_size-2048_q-6-6-6_j-7-7-7_use_day_data-1_avg_pool-0_model_type-scat_filter_key-true.h5 --type scat_cov_pca_25 --experiment_name 666-66 --normalize 0 --latent_dim 32 --cuda 1 --ncluster 9 --filter_key '' --nlayer 12
CUDA_VISIBLE_DEVICES=0 python scripts/train_gmvae.py --h5_filename 3c_window_size-2048_q-6-6-6_j-7-7-7_use_day_data-1_avg_pool-0_model_type-scat_filter_key-true.h5 --type cov_pca_6-6_25 --experiment_name 666-66 --normalize 0 --latent_dim 32 --cuda 1 --ncluster 9 --filter_key '' --nlayer 12
CUDA_VISIBLE_DEVICES=0 python scripts/train_gmvae.py --h5_filename 3c_window_size-2048_q-6-6-6_j-7-7-7_use_day_data-1_avg_pool-0_model_type-scat_filter_key-true.h5 --type scat_cov_pca_75 --experiment_name 666-66 --normalize 0 --latent_dim 32 --cuda 1 --ncluster 9 --filter_key '' --nlayer 12
CUDA_VISIBLE_DEVICES=0 python scripts/train_gmvae.py --h5_filename 3c_window_size-2048_q-6-6-6_j-7-7-7_use_day_data-1_avg_pool-0_model_type-scat_filter_key-true.h5 --type scat_cov_pca_25,cov_pca_6-6_25 --experiment_name 666-66_all --normalize 0 --latent_dim 32 --cuda 1 --ncluster 9 --filter_key '' --nlayer 12
CUDA_VISIBLE_DEVICES=0 python scripts/train_gmvae.py --h5_filename 3c_window_size-2048_q-6-6-6_j-7-7-7_use_day_data-1_avg_pool-0_model_type-scat_filter_key-true.h5 --type scat_cov_pca_25,cov_pca_6-6_75 --experiment_name 666-66_all --normalize 0 --latent_dim 32 --cuda 1 --ncluster 9 --filter_key '' --nlayer 12
CUDA_VISIBLE_DEVICES=0 python scripts/train_gmvae.py --h5_filename 3c_window_size-2048_q-6-6-6_j-7-7-7_use_day_data-1_avg_pool-0_model_type-scat_filter_key-true.h5 --type scat_cov_pca_25,cov_pca_6-6 --experiment_name 666-66_all --normalize 0 --latent_dim 32 --cuda 1 --ncluster 9 --filter_key '' --nlayer 12
