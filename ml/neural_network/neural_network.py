import inspect

import autograd.numpy as np
from matplotlib import pyplot as plt
from sklearn.preprocessing import OneHotEncoder

from ml.initializers import compute_fans
from ml.learning import Learner
from ml.neural_network.activations import Linear
from ml.neural_network.layers import Layer, ParamLayer
from optimization.optimization_function import OptimizationFunction
from optimization.optimizer import LineSearchOptimizer
from optimization.unconstrained.gradient_descent import GradientDescent

plt.style.use('ggplot')


class NeuralNetworkLossFunction(OptimizationFunction):

    def __init__(self, X, y, neural_net, loss, verbose):
        super().__init__(X.shape[1])
        self.X = X
        self.y = y
        self.neural_net = neural_net
        self.loss = loss
        self.verbose = verbose
        self.loss_history = ([], [])  # training loss history, validation loss history
        if not isinstance(self.neural_net.layers[-1]._a, Linear):  # classification
            self.accuracy_history = ([], [])  # training accuracy history, validation loss history

    def args(self):
        return self.X, self.y

    def function(self, packed_weights_biases, X, y):
        self.neural_net._unpack(packed_weights_biases)
        loss = (self.loss(self.neural_net.forward(X), y) +
                np.sum(np.sum(layer.w_reg(layer.W) for layer in self.neural_net.layers
                              if isinstance(layer, ParamLayer)) +
                       np.sum(layer.b_reg(layer.b) for layer in self.neural_net.layers
                              if isinstance(layer, ParamLayer) and layer.use_bias)) / X.shape[0])
        if inspect.stack()[1].function is 'minimize':  # caller's method name
            if self.verbose and self.loss_history[0] and not isinstance(self.neural_net.layers[-1]._a, Linear):
                print('\t accuracy: {:4f}'.format(0.), end='')
            self.loss_history[0].append(loss)
        return loss

    def jacobian(self, packed_weights_biases, X, y):
        """
        The calculation of delta here works with following
        combinations of loss function and output activation:
        mean squared error + identity
        cross entropy + softmax
        binary cross entropy + sigmoid
        """
        y_pred = self.neural_net.forward(X)
        assert y_pred.shape == y.shape
        return self.neural_net._pack(*self.neural_net.backward(y_pred - y))

    def plot(self):
        surface_plot, surface_axes, contour_plot, contour_axes = super().plot()
        # TODO add accuracy plot over iterations
        fig, loss = plt.subplots()
        loss.plot(self.loss_history[0], 'b.', alpha=0.2)
        # loss.plot(self.loss_history[1], 'r-')
        loss.set_title('model loss')
        loss.set_xlabel('epoch')
        loss.set_ylabel('loss')
        loss.legend(['training', 'validation'])
        plt.show()
        if not isinstance(self.neural_net.layers[-1]._a, Linear):  # classification
            fig, accuracy = plt.subplots()
            accuracy.plot(self.accuracy_history[0], 'b.', alpha=0.2)
            accuracy.plot(self.accuracy_history[1], 'r-')
            accuracy.set_title('model accuracy')
            loss.set_xlabel('epoch')
            loss.set_ylabel('accuracy')
            loss.legend(['training', 'validation'])
            plt.show()


class NeuralNetwork(Layer, Learner):

    def __init__(self, *layers):
        assert isinstance(layers, (list, tuple))
        self.layers = layers

    def forward(self, X):
        for layer in self.layers:
            X = layer.forward(X)
        return X

    def backward(self, delta):
        weights_grads = []
        biases_grads = []
        # back propagate
        for layer in self.layers[::-1]:
            if isinstance(layer, ParamLayer):
                delta, grads = layer.backward(delta)
                weights_grads.append(grads['dW'] + layer.w_reg.jacobian(layer.W))
                if layer.use_bias:
                    biases_grads.append(grads['db'] + layer.b_reg.jacobian(layer.b))
            else:
                delta = layer.backward(delta)
        return weights_grads[::-1], biases_grads[::-1]

    @property
    def params(self):
        return ([layer.W for layer in self.layers if isinstance(layer, ParamLayer)],
                [layer.b for layer in self.layers if isinstance(layer, ParamLayer) and layer.use_bias])

    def _pack(self, weights, biases):
        return np.hstack([w.ravel() for w in weights + biases])

    def _unpack(self, packed_weights_biases):
        weight_idx = 0
        bias_idx = 0
        for layer in self.layers:
            if isinstance(layer, ParamLayer):
                start, end, shape = self.weights_idx[weight_idx]
                layer.W = np.reshape(packed_weights_biases[start:end], shape)
                if layer.use_bias:
                    start, end = self.biases_idx[bias_idx]
                    layer.b = packed_weights_biases[start:end]
                    bias_idx += 1
                weight_idx += 1

    def _store_meta_info(self):
        # store meta information for the parameters
        self.weights_idx = []
        self.biases_idx = []
        start = 0
        # save sizes and indices of weights for faster unpacking
        for layer in self.layers:
            if isinstance(layer, ParamLayer):
                end = start + (np.prod(layer.W.shape))
                self.weights_idx.append((start, end, layer.W.shape))
                start = end
        # save sizes and indices of biases for faster unpacking
        for layer in self.layers:
            if isinstance(layer, ParamLayer) and layer.use_bias:
                fan_in, fan_out = compute_fans(layer.b.shape)
                end = start + fan_out
                self.biases_idx.append((start, end))
                start = end

    def fit(self, X, y, loss, optimizer=GradientDescent, learning_rate=0.01, momentum_type='none', momentum=0.9,
            epochs=100, batch_size=None, k_folds=0, max_f_eval=1000, early_stopping=True, verbose=False, plot=False):
        if y.ndim is 1:
            y = y.reshape((-1, 1))
        if not isinstance(self.layers[-1]._a, Linear):  # classification
            y = OneHotEncoder().fit_transform(y).toarray()

        self._store_meta_info()

        packed_weights_biases = self._pack(*self.params)

        loss = NeuralNetworkLossFunction(X, y, self, loss, verbose)
        if issubclass(optimizer, LineSearchOptimizer):
            opt = optimizer(f=loss, wrt=packed_weights_biases, batch_size=batch_size,
                            max_iter=epochs, max_f_eval=max_f_eval, verbose=verbose).minimize()
            # if opt[2] is not 'optimal':
            #     warnings.warn("max_iter or max_f_eval reached and the optimization hasn't converged yet")
        else:
            opt = optimizer(f=loss, wrt=packed_weights_biases, step_rate=learning_rate, momentum_type=momentum_type,
                            momentum=momentum, batch_size=batch_size, max_iter=epochs, verbose=verbose).minimize()
            # if opt[2] is not 'optimal':
            #     warnings.warn("max_iter reached and the optimization hasn't converged yet")
        self._unpack(opt[0])

        if plot:
            loss.plot()

        return self

    def predict(self, X):
        if isinstance(self.layers[-1]._a, Linear):  # regression
            if self.layers[-1].fan_out is 1:  # one target
                return self.forward(X).ravel()
            else:  # multi target
                return self.forward(X)
        else:  # classification
            return np.argmax(self.forward(X), axis=1)
