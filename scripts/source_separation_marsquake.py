"""Script to separate a cluster from given data.
"""

import os
import numpy as np
import torch

from srcsep import generate, analyze, format_tensor
from facvae.utils import (configsdir, parse_input_args, read_config,
                          make_experiment_name, upload_results, checkpointsdir,
                          datadir, MarsMultiscaleDataset)

from facvae.utils import GlitchSeparationSetup, MarsquakeSeparationSetup, plot_deglitching, save_exp_to_h5

from scripts.facvae_trainer import FactorialVAETrainer
from scripts.source_separation import SnippetExtractor

# torch.multiprocessing.set_start_method('spawn', force=True)

# from facvae.utils import plot_deglitching, save_exp_to_h5, SourceSeparationSetup

# Paths to raw Mars waveforms and the scattering covariance thereof.
MARS_PATH = datadir('mars')
MARS_RAW_PATH = datadir(os.path.join(MARS_PATH, 'raw'))
MARS_SCAT_COV_PATH = datadir(os.path.join(MARS_PATH, 'scat_covs_h5'))

# Configuration file.
SRC_SEP_CONFIG_FILE = 'source_separation_marsquake_S1133c.json'

# Random seed.
SEED = 12
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed(SEED)


def optimize(args, x_dataset):
    """Clean a marsquake from a dataset of Mars background data.
    """
    # Setup the marsquake separation by providing the path marsquake json file.
    mars_srcsep = MarsquakeSeparationSetup(MARS_RAW_PATH, args.marsquake)

    # Extract a marsquake from the raw data.
    marsquake = mars_srcsep.get_windowed_marsquake_data(args.window_size)

    # x_dataset = x_dataset[
    #     np.random.permutation(x_dataset.shape[0])[:args.R], :, :]

    for quake_idx in range(marsquake.shape[0]):
        x_obs = marsquake[quake_idx:quake_idx + 1, :, :]

        if args.normalize:
            x_mean = x_dataset.mean(axis=(0, 1))
            x_std = x_dataset.std(axis=(0, 1))
            # Whiten the dataset.
            x_dataset = (x_dataset - x_mean) / (x_std + 1e-8)
            x_obs = (x_obs - x_mean) / (x_std + 1e-8)

        # Realistic scenario: access to a representative (unsupervised) dataset
        # of signals (with the independence regularization).
        deglitching_params = {
            'nks': format_tensor(x_dataset),
            'x_init': format_tensor(x_obs),
            'indep_loss_w': args.indep_loss_w,
            'x_loss_w': args.x_loss_w,
            'fixed_ts': None,
            'cuda': args.cuda
        }
        x_hat = generate(x_obs,
                         x0=x_obs,
                         J=args.j,
                         Q=args.q,
                         wav_type=args.wavelet,
                         it=args.max_itr,
                         tol_optim=args.tol_optim,
                         deglitching_params=deglitching_params,
                         cuda=args.cuda,
                         nchunks=args.nchunks,
                         gpus=[args.gpu_id],
                         exp_name=f'{args.experiment_name}_'
                         f'R-{args.R}_'
                         f'indep_loss_w-{args.indep_loss_w}_'
                         f'x_loss_w-{args.x_loss_w}_'
                         f'normalize-{args.normalize}_'
                         f'marsquake-{args.marsquake}_'
                         f'quake_idx-{quake_idx}')

        if args.normalize:
            # Undo the whitening.
            x_dataset = x_dataset * (x_std + 1e-8) + x_mean
            x_obs = x_obs * (x_std + 1e-8) + x_mean
            x_hat = x_hat * (x_std + 1e-8) + x_mean

        plot_deglitching(args, 'deglitching', x_obs, x_hat)

        # Save the results.
        save_exp_to_h5(os.path.join(checkpointsdir(
            args.experiment), 'reconstruction_' + str(quake_idx) + '.h5'),
                       args,
                       x_obs=x_obs,
                       x_dataset=x_dataset,
                       quake_idx=quake_idx,
                       x_hat=x_hat)

        marsquake[quake_idx, :, :] = x_hat[0, :, :]
        upload_results(cmd_args, flag='--progress')


if __name__ == '__main__':
    # Command line arguments.

    cmd_args = read_config(os.path.join(configsdir(), SRC_SEP_CONFIG_FILE))
    cmd_args = parse_input_args(cmd_args)
    cmd_args.q = [int(j) for j in cmd_args.q.replace(' ', '').split(',')]
    cmd_args.j = [int(j) for j in cmd_args.j.replace(' ', '').split(',')]
    cmd_args.cluster = [
        int(j) for j in cmd_args.cluster.replace(' ', '').split(',')
    ]
    cmd_args.scale = [
        int(j) for j in cmd_args.scale.replace(' ', '').split(',')
    ]
    cmd_args.experiment = make_experiment_name(cmd_args)

    # Read pretrained fVAE configuration from the JSON file specified by
    # cmd_args.
    vae_args = read_config(
        os.path.join(configsdir('fvae_models'), cmd_args.facvae_model))
    vae_args = parse_input_args(vae_args)
    vae_args.experiment = make_experiment_name(vae_args)
    if hasattr(vae_args, 'filter_key'):
        vae_args.filter_key = vae_args.filter_key.replace(' ', '').split(',')
    if hasattr(vae_args, 'scales'):
        vae_args.scales = vae_args.scales.replace(' ', '').split(',')

    if hasattr(cmd_args, 'filter_key'):
        cmd_args.filter_key = cmd_args.filter_key.replace(' ', '').split(',')
        vae_args.filter_key = cmd_args.filter_key

    # Setting default device (cpu/cuda) depending on CUDA availability and
    # input arguments.
    # if torch.cuda.is_available() and cmd_args.cuda:
    #     device = torch.device('cuda')
    # else:
    device = torch.device('cpu')

    # Load data from the Mars dataset
    dataset = MarsMultiscaleDataset(os.path.join(MARS_SCAT_COV_PATH,
                                                 vae_args.h5_filename),
                                    0.90,
                                    scatcov_datasets=vae_args.scales,
                                    load_to_memory=vae_args.load_to_memory,
                                    normalize_data=vae_args.normalize,
                                    filter_key=vae_args.filter_key)

    # Create data loaders for train, validation and test datasets

    if len(dataset.train_idx) < vae_args.batchsize:
        vae_args.batchsize = len(dataset.train_idx)

    train_loader = torch.utils.data.DataLoader(dataset.train_idx,
                                               batch_size=vae_args.batchsize,
                                               shuffle=True,
                                               drop_last=True)
    val_loader = torch.utils.data.DataLoader(dataset.val_idx,
                                             batch_size=vae_args.batchsize,
                                             shuffle=True,
                                             drop_last=False)
    test_loader = torch.utils.data.DataLoader(dataset.test_idx,
                                              batch_size=vae_args.batchsize,
                                              shuffle=False,
                                              drop_last=False)

    # Initialize facvae trainer with the input arguments, dataset, and device
    facvae_trainer = FactorialVAETrainer(vae_args, dataset, device)

    # Load a saved checkpoint for testing.
    network = facvae_trainer.load_checkpoint(vae_args, vae_args.max_epoch - 1)
    # Set the gumbel temperature for sampling from the categorical
    # distribution.
    network.gumbel_temp = np.maximum(
        vae_args.init_temp * np.exp(-vae_args.temp_decay *
                                    (vae_args.max_epoch - 1)),
        vae_args.min_temp)

    snippet_extractor = SnippetExtractor(vae_args, network, dataset,
                                         test_loader, device)

    snippets = snippet_extractor.waveforms_per_scale_cluster(
        vae_args, cmd_args.cluster, cmd_args.scale, sample_size=cmd_args.R)[0]
    snippets = snippets[:, 0:1, :].astype(np.float64)
    optimize(cmd_args, snippets)

    # Upload results to Weights & Biases for tracking training progress.
    upload_results(args, flag='--progress --transfers 8')
