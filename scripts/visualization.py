import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
import numpy as np
import os
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
import torch
from tqdm import tqdm

from facvae.utils import plotsdir

sns.set_style("whitegrid")
font = {'family': 'serif', 'style': 'normal', 'size': 12}
matplotlib.rc('font', **font)
sfmt = matplotlib.ticker.ScalarFormatter(useMathText=True)
sfmt.set_powerlimits((0, 0))
matplotlib.use("Agg")


class Visualization(object):
    """Class visualizing the resuls of a GMVAE training.
    """

    def __init__(self, network, dataset, device):
        self.network = network
        self.dataset = dataset
        self.device = device
        self.colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b',
            '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
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
                x = self.dataset.sample_data(idx)

                # flatten data
                x = x.view(x.size(0), -1)
                y = self.network.inference(x)
                latent_feat = y['mean']
                cluster_membership = y['logits'].argmax(axis=1)

                features[counter:counter +
                         x.size(0), :] = latent_feat.cpu().detach().numpy()[
                             ...]
                clusters[counter:counter + x.size(0)] = cluster_membership.cpu(
                ).detach().numpy()[...]

                counter += x.shape[0]

        return features, clusters

    def plot_waveforms(self, args, data_loader, sample_size=10):
        """Plot waveforms.
        """
        # Sample random data from loader
        x = self.dataset.sample_data(range(len(data_loader.dataset)),
                                     type='scat_cov')
        x = x.to(self.device)

        # Obtain reconstructed data.
        cluster_membership = []
        with torch.no_grad():
            y = self.network(x)
            confident_idxs = y['prob_cat'].max(axis=-1)[0].sort()[1]
            cluster_membership = y['logits'][confident_idxs, :].argmax(axis=1)

        confident_idxs = confident_idxs.cpu()
        cluster_membership = cluster_membership.cpu()
        x = x.cpu()

        figs_axs = [
            plt.subplots(sample_size,
                         args.ncluster,
                         figsize=(8 * args.ncluster, 8 * args.ncluster))
            for i in range(3)
        ]
        names = ['waveform_samples', 'waveform_spectograms', 'scatcov_samples']

        for i in tqdm(range(args.ncluster)):
            cluster_idxs = confident_idxs[np.where(
                cluster_membership == i)[0]][-sample_size:, ...]
            if len(cluster_idxs) > 0:
                waveforms = self.dataset.sample_data(cluster_idxs,
                                                     type='waveform')
                x = self.dataset.sample_data(cluster_idxs, type='scat_cov')

                from IPython import embed; embed()
                for j in range(len(cluster_idxs)):
                    figs_axs[0][1][j, i].plot(waveforms[j, :],
                                              color=self.colors[i % 10],
                                              lw=1.2,
                                              alpha=0.8)
                    figs_axs[0][1][j, i].set_title("Waveform from cluster " +
                                                   str(i))

                    figs_axs[1][1][j, i].specgram(waveforms[j, :],
                                                  Fs=20.0,
                                                  mode='magnitude',
                                                  cmap='jet_r')
                    figs_axs[1][1][j,
                                   i].set_title("Spectrogram from cluster " +
                                                str(i))
                    figs_axs[1][1][j, i].grid(False)

                    figs_axs[2][1][j, i].plot(x[j, :],
                                              color=self.colors[i % 10],
                                              lw=1.2,
                                              alpha=0.8)
                    figs_axs[2][1][j, i].set_title("Scat covs from cluster " +
                                                   str(i))

        for (fig, _), name in zip(figs_axs, names):
            fig.savefig(os.path.join(plotsdir(args.experiment), name + '.png'),
                        format="png",
                        bbox_inches="tight",
                        dpi=100,
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
        x = self.dataset.sample_data(next(iter(data_loader)))
        indices = np.random.randint(0, x.shape[0], size=sample_size)
        x = x[indices, ...]

        # Obtain reconstructed data.
        with torch.no_grad():
            y = self.network(x)
            x_rec = y['x_rec']

        if args.input_size > 2:
            fig, ax = plt.subplots(1, sample_size, figsize=(25, 5))
            for i in range(sample_size):
                ax[i].plot(x[i, :],
                           lw=.8,
                           alpha=1,
                           color='k',
                           label='original')
                ax[i].plot(x_rec[i, :],
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
        features_pca = PCA(n_components=2).fit_transform(features)
        # plot only the first 2 dimensions
        # cmap = plt.cm.get_cmap('hsv', args.ncluster)
        label_colors = {i: self.colors[i] for i in range(args.ncluster)}
        colors = [label_colors[int(i)] for i in clusters]
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

        categorical = torch.nn.functional.one_hot(torch.tensor(indices),
                                                  args.ncluster).float()
        # infer the gaussian distribution according to the category
        mean, var = self.network.generative.pzy(categorical)

        # gaussian random sample by using the mean and variance
        noise = torch.randn_like(var)
        std = torch.sqrt(var)
        gaussian = mean + noise * std

        # generate new samples with the given gaussian
        samples = self.network.generative.pxz(gaussian).cpu().detach().numpy()

        if args.input_size > 2:
            fig, ax = plt.subplots(num_elements,
                                   args.ncluster,
                                   figsize=(8 * args.ncluster,
                                            4 * args.ncluster))
            for i in range(args.ncluster):
                for j in range(num_elements):
                    ax[j, i].plot(samples[i * num_elements + j, :],
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
