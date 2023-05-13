import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
import datetime
import obspy
import numpy as np
from mpire import WorkerPool
from obspy.core import UTCDateTime
import os
from collections import Counter
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from scipy.signal import spectrogram, correlate, correlation_lags
import scipy.signal as signal
import torch
from tqdm import tqdm

from facvae.utils import (plotsdir, create_lmst_xticks, lmst_xtick,
                          roll_zeropad, get_waveform_path_from_time_interval)


# Datastream merge method.
MERGE_METHOD = 1
FILL_VALUE = 'interpolate'


class SnippetExtractor(object):
    """Class visualizing results of a GMVAE training.
    """

    def __init__(self, args, network, dataset, data_loader, device):
        # Pretrained GMVAE network.
        self.network = network
        self.network.eval()
        # The entire dataset.
        self.dataset = dataset
        # Scales.
        self.scales = args.scales
        self.in_shape = {
            scale: dataset.shape['scat_cov'][scale]
            for scale in self.scales
        }
        # Device to perform computations on.
        self.device = device

        (self.cluster_membership, self.cluster_membership_prob,
         self.confident_idxs,
         self.per_cluster_confident_idxs) = self.evaluate_model(
             args, data_loader)

    def get_waveform(self, window_idx, scale):
        window_time_interval = self.get_time_interval(window_idx,
                                                      scale,
                                                      lmst=False)

        filepath = get_waveform_path_from_time_interval(*window_time_interval)

        # Extract some properties of the data to setup HDF5 file.
        data_stream = obspy.read(filepath)
        data_stream = data_stream.merge(method=MERGE_METHOD,
                                        fill_value=FILL_VALUE)
        data_stream = data_stream.detrend(type='spline',
                                            order=2,
                                            dspline=2000,
                                            plot=False)
        data_stream = data_stream.slice(*window_time_interval)

        waveform = np.stack([td.data[-int(scale):] for td in data_stream])

        # Return the required subwindow.
        return waveform.astype(np.float32)

    def get_time_interval(self, window_idx, scale, lmst=True):
        # Extract window time interval.
        window_time_interval = self.dataset.get_time_interval([window_idx])[0]
        # Number of subwindows in the given scale.
        scales = [int(s) for s in self.scales]
        num_sub_windows = max(scales) // int(scale)

        # Example start and end times.
        start_time = window_time_interval[0]
        end_time = window_time_interval[1]

        # Calculate total time duration.
        duration = end_time - start_time

        # Use linspace to create subintervals.
        subinterval_starts = np.linspace(start_time.timestamp,
                                         end_time.timestamp,
                                         num=num_sub_windows + 1)
        subintervals = [
            (UTCDateTime(t1), UTCDateTime(t2))
            for t1, t2 in zip(subinterval_starts[:-1], subinterval_starts[1:])
        ]

        # Select the time interval associated with the given subwindow_idx.
        window_time_interval = subintervals[-1]

        if lmst:
            # Convert to LMST format, usable by matplotlib.
            window_time_interval = (create_lmst_xticks(*window_time_interval,
                                                       time_zone='LMST',
                                                       window_size=int(scale)),
                                    window_time_interval)

        # Return the required time interval.
        return window_time_interval

    def evaluate_model(self, args, data_loader):
        """
        Evaluate the trained FACVAE model.

        Here we pass the data through the trained model and for each window and
        each scale, we extract the cluster membership and the probability of
        the cluster membership. We then sort the windows based on the most
        confident cluster membership.

        Args:
            args: (argparse) arguments containing the model information.
            data_loader: (DataLoader) loader containing the data.
        """

        # Placeholder for cluster membership and probablity for all the data.
        cluster_membership = {
            scale:
            torch.zeros(len(data_loader.dataset),
                        self.dataset.data['scat_cov'][scale].shape[1],
                        dtype=torch.long)
            for scale in self.scales
        }
        cluster_membership_prob = {
            scale:
            torch.zeros(len(data_loader.dataset),
                        self.dataset.data['scat_cov'][scale].shape[1],
                        dtype=torch.float)
            for scale in self.scales
        }

        # Extract cluster memberships.
        for i_idx, idx in enumerate(data_loader):
            # Load data.
            x = self.dataset.sample_data(idx, 'scat_cov')
            # Move to `device`.
            x = {scale: x[scale].to(self.device) for scale in self.scales}
            # Run the input data through the pretrained GMVAE network.
            with torch.no_grad():
                output = self.network(x)
            # Extract the predicted cluster memberships.
            for scale in self.scales:
                cluster_membership[scale][np.sort(idx), :] = output['logits'][
                    scale].argmax(axis=1).reshape(
                        len(idx),
                        self.dataset.data['scat_cov'][scale].shape[1]).cpu()
                cluster_membership_prob[scale][np.sort(idx), :] = output[
                    'prob_cat'][scale].max(axis=1)[0].reshape(
                        len(idx),
                        self.dataset.data['scat_cov'][scale].shape[1]).cpu()

        # Sort indices based on most confident cluster predictions by the
        # network (increasing). The outcome is a dictionary with a key for each
        # scale, where the window indices are stored.
        confident_idxs = {}
        for scale in self.scales:
            # Flatten cluster_membership_prob into a 1D tensor.
            prob_flat = cluster_membership_prob[scale].flatten()

            # Sort the values in the flattened tensor in descending order and
            # return the indices.
            confident_idxs[scale] = torch.argsort(prob_flat,
                                                  descending=True).numpy()

        per_cluster_confident_idxs = {
            scale: {
                str(i): []
                for i in range(args.ncluster)
            }
            for scale in self.scales
        }

        for scale in self.scales:
            for i in range(len(confident_idxs[scale])):
                per_cluster_confident_idxs[scale][str(
                    cluster_membership[scale][confident_idxs[scale]
                                              [i]].item())].append(
                                                  confident_idxs[scale][i])

        return (cluster_membership, cluster_membership_prob, confident_idxs,
                per_cluster_confident_idxs)

    def waveforms_per_scale_cluster(self, args, cluster_idx, scale_idx, sample_size=5):
        """Plot waveforms.
        """

        def do_overlap(pair1, pair2):
            start1, end1 = pair1
            start2, end2 = pair2

            # Check for all types of overlap
            return (start1 <= start2 <= end1 or start1 <= end2 <= end1
                    or start2 <= start1 <= end2 or start2 <= end1 <= end2)

        scale = str(scale_idx)
        i = cluster_idx

        waveforms = {}
        time_intervals = {}
        print('Reading waveforms for scale {}'.format(scale))
        waveforms[scale] = {}
        time_intervals[scale] = {}
        utc_time_intervals = []
        window_idx_list = []
        for sample_idx in range(
                len(self.per_cluster_confident_idxs[scale][str(i)])):
            window_idx = self.per_cluster_confident_idxs[scale][str(
                i)][sample_idx]
            utc_interval = self.get_time_interval(window_idx, scale)[1]
            should_add = True

            for interval in utc_time_intervals:
                if do_overlap(interval, utc_interval):
                    should_add = False
                    break

            if should_add:
                utc_time_intervals.append(utc_interval)
                window_idx_list.append(window_idx)

            if len(window_idx_list) == sample_size:
                break

        waveforms[scale][str(i)] = []
        time_intervals[scale][str(i)] = []
        for window_idx in window_idx_list:
            waveforms[scale][str(i)].append(
                self.get_waveform(window_idx, scale))
            time_intervals[scale][str(i)].append(
                self.get_time_interval(window_idx, scale)[0])

        return waveforms, time_intervals
