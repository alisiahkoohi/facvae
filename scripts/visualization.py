import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
import numpy as np
import os
from collections import Counter
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from scipy.signal import spectrogram
import torch
from tqdm import tqdm

from facvae.utils import plotsdir, create_lmst_xticks, lmst_xtick

sns.set_style("whitegrid")
font = {'family': 'serif', 'style': 'normal', 'size': 18}
matplotlib.rc('font', **font)
sfmt = matplotlib.ticker.ScalarFormatter(useMathText=True)
sfmt.set_powerlimits((0, 0))
matplotlib.use("Agg")

SAMPLING_RATE = 20


class Visualization(object):
    """Class visualizing results of a GMVAE training.
    """

    def __init__(self, network, dataset, window_size, device):
        # Pretrained GMVAE network.
        self.network = network
        self.network.eval()
        # The entire dataset.
        self.dataset = dataset
        # Window size of the dataset.
        self.window_size = window_size
        # Device to perform computations on.
        self.device = device
        # Colors to be used for visualizing different clusters.
        self.colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b',
            '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
        ]
        # All the possible labels that data has. Used for evaluating the
        # clustering performance.
        self.labels = [
            'HIGH_FREQUENCY', 'VERY_HIGH_FREQUENCY', 'LOW_FREQUENCY', '2.4_HZ',
            'SUPER_HIGH_FREQUENCY', 'BROADBAND'
        ]

    def latent_features(self, args, data_loader):
        """Obtain latent features learnt by the model

        Args:
            data_loader: (DataLoader) loader containing the data
            return_labels: (boolean) whether to return true labels or not

        Returns:
           features: (array) array containing the features from the data
        """
        N = len(data_loader.dataset)
        features = np.zeros([N, args.latent_dim])
        clusters = np.zeros([N])
        counter = 0
        with torch.no_grad():
            for idx in data_loader:
                # Load data batch.
                x = self.dataset.sample_data(idx, args.type)

                # flatten data
                x = x.to(self.device)
                y = self.network.inference(x, self.network.gumbel_temp,
                                           self.network.hard_gumbel)
                latent_feat = y['mean']
                cluster_membership = y['logits'].argmax(axis=1)

                features[counter:counter +
                         x.size(0), :] = latent_feat.cpu().detach().numpy()[
                             ...]
                clusters[counter:counter + x.size(0)] = cluster_membership.cpu(
                ).detach().numpy()[...]

                counter += x.shape[0]

        return features, clusters

    def get_times(self, time_intervals, event_list):
        event_times = []
        for event, time_interval in zip(event_list, time_intervals):
            if len(event) > 0:
                time_interval = list(time_interval)
                for inner_idx, _ in enumerate(time_interval):
                    time_interval[inner_idx] = lmst_xtick(
                        time_interval[inner_idx])
                    time_interval[inner_idx] = matplotlib.dates.date2num(
                        time_interval[inner_idx])
                event_times.append(np.array(time_interval).mean())
        return event_times

    def plot_waveforms(self, args, data_loader, sample_size=10):
        """Plot waveforms.
        """
        # Setup the batch index generator.
        idx_loader = torch.utils.data.DataLoader(range(len(
            data_loader.dataset)),
                                                 batch_size=args.batchsize,
                                                 shuffle=False,
                                                 drop_last=False)
        # Placeholder list for cluster membership for all the data.
        cluster_membership = []
        confident_idxs = []
        # Extract cluster memberships.
        for idx in idx_loader:
            # Load data.
            x = self.dataset.sample_data(idx, args.type)
            # Move to `device`.
            x = x.to(self.device)
            # Run the input data through the pretrained GMVAE network.
            with torch.no_grad():
                y = self.network(x)
            # Sort indices based on  most confident cluster predictions by the
            # network (increasing).
            per_batch_confident_idx = y['prob_cat'].max(axis=-1)[0].sort()[1]
            confident_idxs.append(idx[per_batch_confident_idx])
            # Extract the predicted cluster memberships.
            cluster_membership.append(
                y['logits'][per_batch_confident_idx, :].argmax(axis=1))

        # Moving back tensors to CPU for plotting.
        confident_idxs = torch.cat(confident_idxs).cpu().numpy()
        cluster_membership = torch.cat(cluster_membership).cpu().numpy()
        x = x.cpu()

        # List of figures and `ax`s to plot waveforms, spectrograms, and
        # scattering covariances for each cluster.
        figs_axs = [
            plt.subplots(sample_size,
                         args.ncluster,
                         figsize=(8 * args.ncluster, 8 * args.ncluster))
            for i in range(3)
        ]

        fig_hist, ax_hist = plt.subplots(args.ncluster + 2,
                                         1,
                                         figsize=(20, 4 * args.ncluster),
                                         sharex=True)
        # List of file names for each the figures.
        names = ['waveform_samples', 'waveform_spectograms', 'scatcov_samples']

        # Dictionary containing list of all the labels belonging to each
        # predicted cluster.
        cluster_labels = {str(i): [] for i in range(args.ncluster)}
        cluster_drops = {str(i): [] for i in range(args.ncluster)}
        cluster_glitches = {str(i): [] for i in range(args.ncluster)}

        # Find pressure drop times.
        drop_list = self.dataset.get_drops(range(len(data_loader.dataset)))
        # Find glitch times.
        glitch_list = self.dataset.get_glitches(range(len(
            data_loader.dataset)))
        # Find time intervals.
        time_intervals = self.dataset.get_time_interval(
            range(len(data_loader.dataset)))

        # Find the times of pressure drops and glitches.
        drop_times = self.get_times(time_intervals, drop_list)
        glitch_times = self.get_times(time_intervals, glitch_list)

        # Plot the histogram of the pressure drop cluster membership.
        sns.histplot(drop_times,
                     ax=ax_hist[-2],
                     color="k",
                     element="step",
                     alpha=0.3,
                     binwidth=0.01,
                     label='Pressure drops')
        ax_hist[-2].xaxis.set_major_locator(
            matplotlib.dates.HourLocator(interval=3))
        ax_hist[-2].xaxis.set_major_formatter(
            matplotlib.dates.DateFormatter('%H'))
        ax_hist[-2].legend()

        # Plot the histogram of the glitch cluster membership.
        sns.histplot(glitch_times,
                     ax=ax_hist[-1],
                     color="k",
                     element="step",
                     alpha=0.3,
                     binwidth=0.01,
                     label='Glitches')
        ax_hist[-1].xaxis.set_major_locator(
            matplotlib.dates.HourLocator(interval=3))
        ax_hist[-1].xaxis.set_major_formatter(
            matplotlib.dates.DateFormatter('%H'))
        ax_hist[-1].legend()

        # Loop through all the clusters.
        for i in tqdm(range(args.ncluster)):
            cluster_labels[str(i)] = self.dataset.get_labels(
                confident_idxs[np.where(cluster_membership == i)[0]])
            cluster_drops[str(i)] = self.dataset.get_drops(
                confident_idxs[np.where(cluster_membership == i)[0]])
            cluster_glitches[str(i)] = self.dataset.get_glitches(
                confident_idxs[np.where(cluster_membership == i)[0]])
            # Find the `sample_size` most confident data points belonging to
            # cluster `i`

            cluster_idxs = confident_idxs[np.where(cluster_membership == i)[0]]

            if len(cluster_idxs) > 0:
                cluster_times = self.dataset.get_time_interval(cluster_idxs)
                for outer_idx, _ in enumerate(cluster_times):
                    cluster_times[outer_idx] = list(cluster_times[outer_idx])
                    for inner_idx in range(len(cluster_times[outer_idx])):
                        cluster_times[outer_idx][inner_idx] = lmst_xtick(
                            cluster_times[outer_idx][inner_idx])
                        cluster_times[outer_idx][
                            inner_idx] = matplotlib.dates.date2num(
                                cluster_times[outer_idx][inner_idx])
                cluster_times = np.array(cluster_times).mean(-1)
                sns.histplot(cluster_times,
                             ax=ax_hist[i],
                             color=self.colors[i % 10],
                             element="step",
                             alpha=0.3,
                             binwidth=0.005,
                             label='cluster ' + str(i) + ' - ' +
                             str(len(cluster_times)))
                ax_hist[i].xaxis.set_major_locator(
                    matplotlib.dates.HourLocator(interval=3))
                ax_hist[i].xaxis.set_major_formatter(
                    matplotlib.dates.DateFormatter('%H'))
                ax_hist[i].legend()

                cluster_idxs = cluster_idxs[-sample_size:, ...]

                waveforms = self.dataset.sample_data(cluster_idxs,
                                                     type='waveform')
                x = self.dataset.sample_data(cluster_idxs, args.type)

                x = self.dataset.unnormalize(x, args.type)
                waveforms = self.dataset.unnormalize(waveforms, 'waveform')
                waveform_times = self.dataset.get_time_interval(cluster_idxs)

                for j in range(len(cluster_idxs)):

                    figs_axs[0][1][j, i].plot_date(create_lmst_xticks(
                        *waveform_times[j],
                        time_zone='LMST',
                        window_size=self.window_size),
                                                   waveforms[j, 0, :],
                                                   xdate=True,
                                                   color=self.colors[i % 10],
                                                   lw=1.2,
                                                   alpha=0.8,
                                                   fmt='')
                    figs_axs[0][1][j, i].xaxis.set_major_locator(
                        matplotlib.dates.MinuteLocator(interval=10))
                    figs_axs[0][1][j, i].xaxis.set_major_formatter(
                        matplotlib.dates.DateFormatter('%H:%M'))
                    figs_axs[0][1][j, i].set_ylim([-5e-7, 5e-7])
                    figs_axs[0][1][j, i].set_title("Waveform from cluster " +
                                                   str(i))
                    
                    figs_axs[1][1][j, i].set_ylim(0.1, SAMPLING_RATE / 2)
                    figs_axs[1][1][j, i].specgram(waveforms[j, 0, :],
                                                  Fs=SAMPLING_RATE,
                                                  mode='magnitude',
                                                  cmap='RdYlBu_r')
                    figs_axs[1][1][j, i].set_ylim(0.1, SAMPLING_RATE / 2)
                    figs_axs[1][1][j, i].set_yscale("log")
                    figs_axs[1][1][j,
                                   i].set_title("Spectrogram from cluster " +
                                                str(i))
                    figs_axs[1][1][j, i].grid(False)

                    figs_axs[2][1][j, i].plot(x[j, 0, :],
                                              color=self.colors[i % 10],
                                              lw=1.2,
                                              alpha=0.8)
                    figs_axs[2][1][j, i].set_title("Scat covs from cluster " +
                                                   str(i))

        fig_hist.savefig(os.path.join(plotsdir(args.experiment),
                                      'cluster_time_dist.png'),
                         format="png",
                         bbox_inches="tight",
                         dpi=200,
                         pad_inches=.05)
        plt.close(fig_hist)

        for (fig, _), name in zip(figs_axs, names):
            fig.savefig(os.path.join(plotsdir(args.experiment), name + '.png'),
                        format="png",
                        bbox_inches="tight",
                        dpi=100,
                        pad_inches=.05)
            plt.close(fig)

        label_count_per_cluster = {str(i): {} for i in range(args.ncluster)}
        drop_count_per_cluster = {str(i): 0 for i in range(args.ncluster)}
        glitch_count_per_cluster = {str(i): 0 for i in range(args.ncluster)}
        for i in range(args.ncluster):
            for label in self.labels:
                label_count_per_cluster[str(i)][label] = 0
            per_cluster_label_list = []
            for label in cluster_labels[str(i)]:
                for v in label:
                    per_cluster_label_list.append(v)
            for drop in cluster_drops[str(i)]:
                drop_count_per_cluster[str(i)] += len(drop)
            for glitch in cluster_glitches[str(i)]:
                glitch_count_per_cluster[str(i)] += len(glitch)
            count = dict(Counter(per_cluster_label_list))
            for key, value in count.items():
                label_count_per_cluster[str(i)][key] = value

            fig = plt.figure(figsize=(8, 6))
            plt.bar(
                range(args.ncluster),
                [drop_count_per_cluster[str(i)] for i in range(args.ncluster)],
                label='Pressure drops',
                color="k")
            plt.xlabel('Clusters')
            plt.ylabel('Pressure drop count')
            plt.title('Pressure drop count per cluster')
            plt.legend(ncol=2, fontsize=12)
            plt.gca().set_xticks(range(args.ncluster))
            fig.savefig(os.path.join(plotsdir(args.experiment),
                                     'pressure_drop_count.png'),
                        format="png",
                        bbox_inches="tight",
                        dpi=200,
                        pad_inches=.05)
            plt.close(fig)

            fig = plt.figure(figsize=(8, 6))
            plt.bar(range(args.ncluster), [
                glitch_count_per_cluster[str(i)] for i in range(args.ncluster)
            ],
                    label='Glitches',
                    color="k")
            plt.xlabel('Clusters')
            plt.ylabel('Glitch count')
            plt.title('Glitch count per cluster')
            plt.legend(ncol=2, fontsize=12)
            plt.gca().set_xticks(range(args.ncluster))
            fig.savefig(os.path.join(plotsdir(args.experiment),
                                     'glitch_count.png'),
                        format="png",
                        bbox_inches="tight",
                        dpi=200,
                        pad_inches=.05)
            plt.close(fig)

        for j, label in enumerate(self.labels):
            fig = plt.figure(figsize=(8, 6))
            cluster_per_label = []
            for i in range(args.ncluster):
                cluster_per_label.append(
                    label_count_per_cluster[str(i)][label])
            plt.bar(range(args.ncluster),
                    cluster_per_label,
                    label=label,
                    color=self.colors[j % 10])
            plt.xlabel('Clusters')
            plt.ylabel('Event count')
            plt.title('Event count per cluster')
            plt.legend(ncol=2, fontsize=12)
            plt.gca().set_xticks(range(args.ncluster))
            fig.savefig(os.path.join(plotsdir(args.experiment),
                                     'event_count' + label + '.png'),
                        format="png",
                        bbox_inches="tight",
                        dpi=200,
                        pad_inches=.05)
            plt.close(fig)

        fig = plt.figure(figsize=(8, 6))
        for j, label in enumerate(self.labels):
            cluster_per_label = []
            for i in range(args.ncluster):
                cluster_per_label.append(
                    label_count_per_cluster[str(i)][label])
            plt.bar(range(args.ncluster),
                    cluster_per_label,
                    label=label,
                    color=self.colors[j % 10])
        plt.xlabel('Clusters')
        plt.ylabel('Event count')
        plt.title('Event count per cluster')
        plt.legend(ncol=2, fontsize=12)
        plt.gca().set_xticks(range(args.ncluster))
        fig.savefig(os.path.join(plotsdir(args.experiment), 'event_count.png'),
                    format="png",
                    bbox_inches="tight",
                    dpi=200,
                    pad_inches=.05)
        plt.close(fig)

        with open(
                os.path.join(plotsdir(args.experiment),
                             'label-distribution.txt'), 'w') as f:
            print('label distribution')
            for key, value in cluster_labels.items():
                per_cluster_label_list = []
                for label in value:
                    for v in label:
                        per_cluster_label_list.append(v)
                f.write(key + ': ' + str(len(per_cluster_label_list)) + '\n')
                print(key, len(per_cluster_label_list))

        with open(
                os.path.join(plotsdir(args.experiment),
                             'waveforms-per-cluster.txt'), 'w') as f:
            print('number of waveforms per cluster')
            for key in cluster_labels.keys():
                cluster_idxs = confident_idxs[np.where(
                    cluster_membership == int(key))[0]]
                f.write(key + ': ' + str(len(cluster_idxs)) + '\n')
                print(key, len(cluster_idxs))

    def plot_clusters(self, args, data_loader):
        """Plot predicted clusters.
        """
        # Load all the data to cluster.
        x = self.dataset.sample_data(range(len(data_loader.dataset)),
                                     args.type)
        # Move to `device`.
        x = x.to(self.device)
        # Placeholder list for cluster membership for all the data.
        cluster_membership = []

        # Extract cluster memberships.
        with torch.no_grad():
            # Run the input data through the pretrained GMVAE network.
            y = self.network(x)
            # Extract the predicted cluster memberships.
            cluster_membership = y['logits'].argmax(axis=1)

        # Moving back tensors to CPU for plotting.
        cluster_membership = cluster_membership.cpu()
        x = x.cpu()
        if args.dataset == 'mars':
            x = self.dataset.unnormalize(x, args.type)

        fig = plt.figure(figsize=(8, 6))
        for i in range(args.ncluster):
            cluster_idxs = np.where(cluster_membership == i)[0]
            plt.scatter(x[cluster_idxs, 0],
                        x[cluster_idxs, 1],
                        color=self.colors[i % 10],
                        s=2,
                        alpha=0.5)
        plt.title('Predicted cluster membership')
        # ax[i].axis('off')
        plt.savefig(os.path.join(plotsdir(args.experiment),
                                 'clustered_samples.png'),
                    format="png",
                    bbox_inches="tight",
                    dpi=300,
                    pad_inches=.05)
        plt.close(fig)

    def reconstruct_data(self, args, data_loader, sample_size=5):
        """Reconstruct Data

        Args:
            data_loader: (DataLoader) loader containing the data
            sample_size: (int) size of random data to consider from data_loader

        Returns:
            reconstructed: (array) array containing the reconstructed data
        """
        # Sample random data from loader
        x = self.dataset.sample_data(next(iter(data_loader)), args.type)
        indices = np.random.randint(0, x.shape[0], size=sample_size)
        x = x[indices, ...]
        x = x.to(self.device)

        # Obtain reconstructed data.
        with torch.no_grad():
            y = self.network(x)
            x_rec = y['x_rec']

        x = x.cpu()
        x_rec = x_rec.cpu()

        if x.shape[-1] > 2:
            fig, ax = plt.subplots(1, sample_size, figsize=(25, 5))
            for i in range(sample_size):
                ax[i].plot(x[i, 0, :],
                           lw=.8,
                           alpha=1,
                           color='k',
                           label='original')
                ax[i].plot(x_rec[i, 0, :],
                           lw=.8,
                           alpha=0.5,
                           color='r',
                           label='reconstructed')
            plt.legend()
            plt.savefig(os.path.join(plotsdir(args.experiment), 'rec.png'),
                        format="png",
                        bbox_inches="tight",
                        dpi=300,
                        pad_inches=.05)
            plt.close(fig)
        else:
            fig, ax = plt.subplots(1, 2, figsize=(10, 5))
            ax[0].scatter(x[:, 0],
                          x[:, 1],
                          s=2,
                          alpha=0.5,
                          color='k',
                          label='original')
            ax[1].scatter(x_rec[:, 0],
                          x_rec[:, 1],
                          s=2,
                          alpha=0.5,
                          color='r',
                          label='reconstructed')
            plt.legend()
            plt.savefig(os.path.join(plotsdir(args.experiment), 'rec.png'),
                        format="png",
                        bbox_inches="tight",
                        dpi=300,
                        pad_inches=.05)
            plt.close(fig)

        if args.dataset == 'mars':
            x = self.dataset.unnormalize(x, args.type)
            x_rec = self.dataset.unnormalize(x_rec, args.type)

            fig, ax = plt.subplots(1, sample_size, figsize=(25, 5))
            for i in range(sample_size):
                ax[i].plot(x[i, 0, :],
                           lw=.8,
                           alpha=1,
                           color='k',
                           label='original')
                ax[i].plot(x_rec[i, 0, :],
                           lw=.8,
                           alpha=0.5,
                           color='r',
                           label='reconstructed')
            plt.legend()
            plt.savefig(os.path.join(plotsdir(args.experiment),
                                     'rec_unnormalized.png'),
                        format="png",
                        bbox_inches="tight",
                        dpi=300,
                        pad_inches=.05)
            plt.close(fig)

    def plot_latent_space(self, args, data_loader, save=False):
        """Plot the latent space learnt by the model

        Args:
            data: (array) corresponding array containing the data
            labels: (array) corresponding array containing the labels
            save: (bool) whether to save the latent space plot

        Returns:
            fig: (figure) plot of the latent space
        """
        # obtain the latent features
        features, clusters = self.latent_features(args, data_loader)
        features_tsne = TSNE(n_components=2,
                             learning_rate='auto',
                             init='pca',
                             early_exaggeration=10,
                             perplexity=200).fit_transform(features)

        # plot only the first 2 dimensions
        # cmap = plt.cm.get_cmap('hsv', args.ncluster)
        label_colors = {i: self.colors[i % 10] for i in range(args.ncluster)}
        colors = [label_colors[int(i)] for i in clusters]

        if features.shape[-1] > 2:
            features_pca = PCA(n_components=2).fit_transform(features)
            fig = plt.figure(figsize=(8, 6))
            plt.scatter(features_pca[:, 0],
                        features_pca[:, 1],
                        marker='o',
                        c=colors,
                        edgecolor='none',
                        cmap=plt.cm.get_cmap('jet', 10),
                        s=10)
            plt.title("Two dimensional PCA of the latent samples")
            plt.savefig(os.path.join(plotsdir(args.experiment),
                                     'pca_latent_space.png'),
                        format="png",
                        bbox_inches="tight",
                        dpi=300,
                        pad_inches=.05)
            plt.close(fig)
        else:
            fig = plt.figure(figsize=(8, 6))
            plt.scatter(features[:, 0],
                        features[:, 1],
                        marker='o',
                        c=colors,
                        edgecolor='none',
                        cmap=plt.cm.get_cmap('jet', 10),
                        s=10)

            plt.title("Latent samples")
            plt.savefig(os.path.join(plotsdir(args.experiment),
                                     'pca_latent_space.png'),
                        format="png",
                        bbox_inches="tight",
                        dpi=300,
                        pad_inches=.05)
            plt.close(fig)

        fig = plt.figure(figsize=(8, 6))
        plt.scatter(features_tsne[:, 0],
                    features_tsne[:, 1],
                    marker='o',
                    c=colors,
                    edgecolor='none',
                    cmap=plt.cm.get_cmap('jet', 10),
                    s=10)
        plt.title("T-SNE visualization of the latent samples")
        plt.savefig(os.path.join(plotsdir(args.experiment),
                                 'latent_space_tsne.png'),
                    format="png",
                    bbox_inches="tight",
                    dpi=300,
                    pad_inches=.05)
        plt.close(fig)

    def random_generation(self, args, num_elements=3):
        """Random generation for each category

        Args:
            num_elements: (int) number of elements to generate

        Returns:
            generated data according to num_elements
        """
        # categories for each element
        arr = np.array([])
        for i in range(args.ncluster):
            arr = np.hstack([arr, np.ones(num_elements) * i])
        indices = arr.astype(int).tolist()

        categorical = torch.nn.functional.one_hot(
            torch.tensor(indices), args.ncluster).float().to(self.device)
        # infer the gaussian distribution according to the category
        mean, var = self.network.generative.pzy(categorical)

        # gaussian random sample by using the mean and variance
        noise = torch.randn_like(var)
        std = torch.sqrt(var)
        gaussian = mean + noise * std

        # generate new samples with the given gaussian
        gaussian = gaussian.to(self.device)
        samples = self.network.generative.pxz(gaussian).cpu().detach().numpy()

        if samples.shape[-1] > 2:
            fig, ax = plt.subplots(num_elements,
                                   args.ncluster,
                                   figsize=(8 * args.ncluster,
                                            4 * args.ncluster))
            for i in range(args.ncluster):
                for j in range(num_elements):
                    ax[j, i].plot(samples[i * num_elements + j, 0, :],
                                  color=self.colors[i % 10],
                                  lw=1.2,
                                  alpha=0.8)
                    ax[j, i].set_title("Sample from cluster " + str(i))
            plt.savefig(os.path.join(plotsdir(args.experiment),
                                     'joint_samples.png'),
                        format="png",
                        bbox_inches="tight",
                        dpi=300,
                        pad_inches=.05)
            plt.close(fig)
        else:
            fig = plt.figure(figsize=(8, 6))
            for i in range(args.ncluster):
                plt.scatter(samples[i * num_elements:(i + 1) * num_elements,
                                    0],
                            samples[i * num_elements:(i + 1) * num_elements,
                                    1],
                            color=self.colors[i % 10],
                            s=2,
                            alpha=0.5)
            plt.title('Generated joint samples')
            # ax[i].axis('off')
            plt.savefig(os.path.join(plotsdir(args.experiment),
                                     'joint_samples.png'),
                        format="png",
                        bbox_inches="tight",
                        dpi=300,
                        pad_inches=.05)
            plt.close(fig)
