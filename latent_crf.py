import numpy as np
from crf import MultinomialFixedGraphCRF
from pyqpbo import alpha_expansion_graph

from IPython.core.debugger import Tracer
tracer = Tracer()


class LatentFixedGraphCRF(MultinomialFixedGraphCRF):
    """CRF with general graph that is THE SAME for all examples.
    graph is given by scipy sparse adjacency matrix.
    """
    def __init__(self, n_labels, n_states_per_label, graph):
        self.n_states_per_label = n_states_per_label
        n_states = n_labels * n_states_per_label
        super(LatentFixedGraphCRF, self).__init__(n_states, graph)
        # n_labels unary parameters, upper triangular for pairwise
        self.n_states = n_states

    def psi(self, x, h):
        # x is unaries
        # h is latent labeling
        ## unary features:
        x_wide = np.repeat(x, self.n_states_per_label, axis=1)
        return super(LatentFixedGraphCRF, self).psi(x_wide, h)

    def inference(self, x, w):
        # augment unary potentials for latent states
        x_wide = np.repeat(x, self.n_states_per_label, axis=1)
        # do usual inference
        h = super(LatentFixedGraphCRF, self).inference(x_wide, w)
        return h

    def loss_augmented_inference(self, x, h, w):
        # augment unary potentials for latent states
        x_wide = np.repeat(x, self.n_states_per_label, axis=1)
        # do usual inference
        x_wide = np.repeat(x, self.n_states_per_label, axis=1)
        unary_params = w[:self.n_states].copy()
        # avoid division by zero:
        unary_params[unary_params == 0] = 1e-10
        for s in np.arange(self.n_states):
            # for each class, decrement unaries
            # for loss-agumention
            x_wide[h / self.n_states_per_label
                    != s / self.n_states_per_label, s] += 1. / unary_params[s]
        # augment unary potentials for latent states
        # do usual inference
        h = super(LatentFixedGraphCRF, self).inference(x_wide, w)
        # create y from h:
        return h

    def latent(self, x, y, w):
        # augment unary potentials for latent states
        x_wide = np.repeat(x, self.n_states_per_label, axis=1)
        # do usual inference
        unary_params = w[:self.n_states]
        pairwise_flat = np.asarray(w[self.n_states:])
        pairwise_params = np.zeros((self.n_states, self.n_states))
        pairwise_params[np.tri(self.n_states, dtype=np.bool)] = pairwise_flat
        pairwise_params = pairwise_params + pairwise_params.T\
                - np.diag(np.diag(pairwise_params))
        unaries = (- 10 * unary_params * x_wide).astype(np.int32)
        # forbid h that is incompoatible with y
        # by modifying unary params
        other_states = (np.arange(self.n_states) / self.n_states_per_label !=
                y[:, np.newaxis])
        unaries[other_states] = +1000000
        pairwise = (-10 * pairwise_params).astype(np.int32)
        h = alpha_expansion_graph(self.edges, unaries, pairwise)
        if (h / self.n_states_per_label != y).any():
            if np.any(w):
                print("inconsistent h and y")
                #tracer()
                h = y * self.n_states_per_label
            else:
                h = y * self.n_states_per_label
        return h

    def loss(self, h, h_hat):
        return np.sum(h / self.n_states_per_label
                != h_hat / self.n_states_per_label)
