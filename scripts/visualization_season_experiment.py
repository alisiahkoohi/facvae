import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
import datetime
import numpy as np
import os
from tqdm import tqdm

from facvae.utils import plotsdir

sns.set_style("white")
font = {'family': 'serif', 'style': 'normal', 'size': 18}
matplotlib.rc('font', **font)
sfmt = matplotlib.ticker.ScalarFormatter(useMathText=True)
sfmt.set_powerlimits((0, 0))
matplotlib.use("Agg")

SAMPLING_RATE = 20

# Datastream merge method.
MERGE_METHOD = 1
FILL_VALUE = 'interpolate'

PATHS = [
    plotsdir(
        'nature_full-mission_max_epoch-1000_batchsize-16384_lr-0.001_lr_final-0.001_ncluster-9_latent_dim-32_w_rec-0.15_wd-0.0_hidden_dim-1024_nlayer-4_window_size-65536_scales-1024-4096-16384-65536_seed-29_full_summer1-2'
    ),
    plotsdir(
        'nature_full-mission_max_epoch-1000_batchsize-16384_lr-0.001_lr_final-0.001_ncluster-9_latent_dim-32_w_rec-0.15_wd-0.0_hidden_dim-1024_nlayer-4_window_size-65536_scales-1024-4096-16384-65536_seed-29_full_fall1-2'
    ),
    # plotsdir(
    #     'nature_full-mission_max_epoch-1000_batchsize-16384_lr-0.001_lr_final-0.001_ncluster-9_latent_dim-32_w_rec-0.15_wd-0.0_hidden_dim-1024_nlayer-4_window_size-65536_scales-1024-4096-16384-65536_seed-29_full_winter1'
    # ),
    plotsdir(
        'nature_full-mission_max_epoch-1000_batchsize-16384_lr-0.001_lr_final-0.001_ncluster-9_latent_dim-32_w_rec-0.15_wd-0.0_hidden_dim-1024_nlayer-4_window_size-65536_scales-1024-4096-16384-65536_seed-29_full_spring1-2'
    )
]

color_codes = [
    "#c92020", "#15992a", "#1e3ec9", "#1e3ec9", "#aab304", "#c92020", "#d48955"
]

cluster_idx_coverter = {
    '1024': [
        lambda i: [0, 1, 2, 3, 4, 5, 6, 7, 8][i],
        lambda i: [0, 1, 2, 3, 4, 5, 6, 7, 8][i],
        lambda i: [0, 1, 2, 3, 4, 5, 6, 7, 8][i],
    ],
    '4096': [
        lambda i: [0, 1, 2, 3, 4, 5, 6, 7, 8][i],
        lambda i: [0, 1, 2, 3, 4, 5, 6, 7, 8][i],
        lambda i: [0, 1, 2, 3, 4, 5, 6, 7, 8][i],
    ],
    '16384': [
        lambda i: [0, 1, 2, 3, 4, 5, 6, 7, 8][i],
        lambda i: [0, 1, 2, 3, 4, 5, 6, 7, 8][i],
        lambda i: [0, 1, 2, 3, 4, 5, 6, 7, 8][i],
    ],
    '65536': [
        lambda i: [0, 1, 2, 3, 4, 5, 6, 7, 8][i],
        lambda i: [0, 1, 2, 3, 4, 5, 6, 7, 8][i],
        lambda i: [0, 1, 2, 3, 4, 5, 6, 7, 8][i],
    ]
}

# Plot histogram of cluster times.
for cluster in range(9):
    print('Plotting time histograms for cluster {}'.format(cluster))
    for scale in tqdm(['1024', '4096', '16384', '65536']):
        fig = plt.figure(figsize=(5, 1.5))
        for i, path in enumerate(PATHS):
            mid_time_intervals = np.load(os.path.join(
                path, 'mid_time_intervals.npy'),
                                         allow_pickle=True).item()
            sns.histplot(
                mid_time_intervals[scale][str(
                    cluster_idx_coverter[scale][i](cluster))],
                color=color_codes[i % len(color_codes)],
                element="step",
                alpha=0.3,
                binwidth=0.005,
                label=['Summer', 'Fall', 'Spring'][i],
                kde=False,
                stat='density',
            )
            #  label='cluster ' + str(cluster))
        ax = plt.gca()
        ax.set_ylabel('')
        plt.legend(loc="upper left", fontsize=9, ncol=3)
        ax.set_xlim([
            matplotlib.dates.date2num(datetime.datetime(
                1900, 1, 1, 0, 0, 0, 0)),
            matplotlib.dates.date2num(
                datetime.datetime(1900, 1, 1, 23, 59, 59, 999999)),
        ])
        ax.xaxis.set_major_locator(matplotlib.dates.HourLocator(interval=5))
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H'))
        # ax.legend(fontsize=12)
        ax.set_yticklabels([])
        ax.tick_params(axis='both', which='major', labelsize=10)
        plt.savefig(os.path.join(
            plotsdir(os.path.join('season_experiment', 'scale_' + scale)),
            'time_histogram_cluster-' + str(cluster) + '.png'),
                    format="png",
                    bbox_inches="tight",
                    dpi=200,
                    pad_inches=.02)
        plt.close(fig)
