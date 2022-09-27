import torch
import numpy as np
from torch.nn import functional as F


class LossFunctions(object):
    """Loss functions for the GMVAE."""

    eps = 1e-8

    def reconstruction_loss(self, real, predicted, rec_type='mse'):
        """Reconstruction loss between the true and predicted outputs
        mse = (1/n)*Σ(real - predicted)^2
        bce = (1/n) * -Σ(real*log(predicted) + (1 - real)*log(1 - predicted))

        Args:
            real: (array) corresponding array containing the true labels
            predictions: (array) corresponding array containing the predicted labels

        Returns:
            output: (array/float) depending on average parameters the result will be the mean
                            of all the sample losses or an array with the losses per sample
        """
        if rec_type == 'mse':
            loss = (real - predicted).pow(2)
        elif rec_type == 'bce':
            loss = F.binary_cross_entropy(predicted, real, reduction='none')
        else:
            raise "invalid loss function... try bce or mse..."
        return loss.sum(-1).mean()

    def log_normal(self, x, mu, var):
        """Logarithm of normal distribution with mean=mu and variance=var
        log(x|μ, σ^2) = loss = -0.5 * Σ log(2π) + log(σ^2) + ((x - μ)/σ)^2

        Args:
            x: (array) corresponding array containing the input
            mu: (array) corresponding array containing the mean
            var: (array) corresponding array containing the variance

        Returns:
            output: (array/float) depending on average parameters the result will be the mean
                of all the sample losses or an array with the losses per sample
        """
        if self.eps > 0.0:
            var = var + self.eps
        return -0.5 * torch.sum(
            np.log(2.0 * np.pi) + torch.log(var) + torch.pow(x - mu, 2) / var,
            dim=-1)

    def gaussian_loss(self, z, z_mu, z_var, z_mu_prior, z_var_prior):
        """Variational loss when using labeled data without considering reconstruction loss
        loss = log q(z|x,y) - log p(z) - log p(y)

        Args:
            z: (array) array containing the gaussian latent variable
            z_mu: (array) array containing the mean of the inference model
            z_var: (array) array containing the variance of the inference model
            z_mu_prior: (array) array containing the prior mean of the generative model
            z_var_prior: (array) array containing the prior variance of the generative mode

        Returns:
            output: (array/float) depending on average parameters the result will be the mean
                of all the sample losses or an array with the losses per sample
        """
        loss = self.log_normal(z, z_mu, z_var) - self.log_normal(
            z, z_mu_prior, z_var_prior)
        return loss.mean()

    def gaussian_loss(self, z, z_mu, z_var, z_mu_prior, z_var_prior):
        """Variational loss when using labeled data without considering reconstruction loss
        loss = log q(z|x,y) - log p(z) - log p(y)

        Args:
            z: (array) array containing the gaussian latent variable
            z_mu: (array) array containing the mean of the inference model
            z_var: (array) array containing the variance of the inference model
            z_mu_prior: (array) array containing the prior mean of the generative model
            z_var_prior: (array) array containing the prior variance of the generative mode

        Returns:
            output: (array/float) depending on average parameters the result will be the mean
                of all the sample losses or an array with the losses per sample
        """
        loss = self.log_normal(z, z_mu, z_var) - self.log_normal(
            z, z_mu_prior, z_var_prior)
        return loss.mean()

    def gaussian_closed_form_loss(self, mu_q, var_q, mu_p, var_p):

        loss = -0.5 * mu_q.shape[-1]
        loss += 0.5 * (torch.sum(torch.log(var_p), dim=-1) -
                       torch.sum(torch.log(var_q), dim=-1))
        loss += 0.5 * torch.sum(var_q / var_p, dim=-1)
        loss += 0.5 * torch.sum(torch.pow(mu_p - mu_q, 2) / var_p, dim=-1)
        return loss.mean()


    def entropy(self, logits, targets):
        """Entropy loss
        loss = (1/n) * -Σ targets*log(predicted)

        Args:
          logits: (array) corresponding array containing the logits of the categorical variable
          real: (array) corresponding array containing the true labels

        Returns:
          output: (array/float) depending on average parameters the result will be the mean
                                of all the sample losses or an array with the losses per sample
        """
        log_q = F.log_softmax(logits, dim=-1)
        return -torch.mean(torch.sum(targets * log_q, dim=-1))
