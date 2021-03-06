import numpy as np

from ml.initializers import glorot_uniform, zeros
from ml.neural_network.activations import Activation
from ml.regularizers import l2


class Layer:

    def forward(self, X):
        raise NotImplementedError

    def backward(self, delta):
        raise NotImplementedError


class ParamLayer(Layer):

    def __init__(self, w_shape, activation, w_init, b_init, w_reg, b_reg, use_bias):

        if isinstance(activation, Activation):
            self._a = activation
        else:
            raise TypeError

        if w_init is None:
            self.W = glorot_uniform(w_shape)
        else:
            self.W = w_init(w_shape)

        self.use_bias = use_bias
        if self.use_bias:
            shape = [1] * len(w_shape)
            shape[-1] = w_shape[-1]
            if b_init is None:
                self.b = zeros(shape)
            else:
                self.b = b_init(shape)

        if w_reg is None:
            self.w_reg = l2
        else:
            self.w_reg = w_reg

        if b_reg is None:
            self.b_reg = l2
        else:
            self.b_reg = b_reg


class FullyConnected(ParamLayer):
    def __init__(self, n_in, n_out, activation, w_init=glorot_uniform, b_init=zeros, w_reg=l2, b_reg=l2, use_bias=True):
        super().__init__((n_in, n_out), activation, w_init, b_init, w_reg, b_reg, use_bias)
        self.fan_in = n_in
        self.fan_out = n_out

    def forward(self, X):
        self._X = X
        self._WX_b = self._X.dot(self.W)
        if self.use_bias:
            self._WX_b += self.b
        return self._a(self._WX_b)

    def backward(self, delta):
        # dW, db
        dZ = delta * self._a.jacobian(self._WX_b)
        grads = {'dW': self._X.T.dot(dZ)}
        if self.use_bias:
            grads['db'] = np.sum(dZ, axis=0, keepdims=True)
        # dX
        dX = dZ.dot(self.W.T)
        return dX, grads


class Conv2D(ParamLayer):
    def __init__(self, in_channels, out_channels, kernel_size=(3, 3), strides=(1, 1), padding='valid',
                 channels_last=True, activation=None, w_init=glorot_uniform, b_init=zeros,
                 w_reg=l2, b_reg=l2, use_bias=True):
        super().__init__((in_channels,) + kernel_size + (out_channels,),
                         activation, w_init, b_init, w_reg, b_reg, use_bias)
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.kernel_size = kernel_size
        self.strides = strides
        self.padding = padding.lower()
        if padding not in ('valid', 'same'):
            raise ValueError('unknown padding type {}'.format(padding))
        self.channels_last = channels_last

    def convolution(self, x, flt, conved):
        batch_size = x.shape[0]
        t_flt = flt.transpose((1, 2, 0, 3))  # [c,h,w,out] => [h,w,c,out]
        s0, s1, k0, k1 = self.strides + tuple(flt.shape[1:3])
        for i in range(0, conved.shape[1]):  # in each row of the convoluted feature map
            for j in range(0, conved.shape[2]):  # in each column of the convoluted feature map
                x_seg_matrix = x[:, i * s0:i * s0 + k0, j * s1:j * s1 + k1, :].reshape(
                    (batch_size, -1))  # [n,h,w,c] => [n, h*w*c]
                flt_matrix = t_flt.reshape((-1, flt.shape[-1]))  # [h,w,c, out] => [h*w*c, out]
                filtered = x_seg_matrix.dot(flt_matrix)  # sum of filtered window [n, out]
                conved[:, i, j, :] = filtered
        return conved

    def forward(self, X):
        self._X = X
        if not self.channels_last:  # channels_first
            # [batch, channel, height, width] => [batch, height, width, channel]
            self._X = np.transpose(self._X, (0, 2, 3, 1))
        # padded dim from top, bottom, left, right
        self._padded, tmp_conved, self._p_tblr = get_padded_and_tmp_out(
            self._X, self.kernel_size, self.strides, self.out_channels, self.padding)

        # convolution
        self._WX_b = self.convolution(self._padded, self.W, tmp_conved)
        if self.use_bias:
            self._WX_b += self.b

        self._activated = self._a(self._WX_b)
        return self._activated if self.channels_last else self._activated.transpose((0, 3, 1, 2))

    def backward(self, delta):
        # according to:
        # https://medium.com/@2017csm1006/forward-and-backpropagation-in-convolutional-neural-network-4dfa96d7b37e
        dZ = delta * self._a.jacobian(self._WX_b)

        # dW, db
        dW = np.empty_like(self.W)  # [c,h,w,out]
        dW = self.convolution(self._padded.transpose((3, 1, 2, 0)), dZ, dW)

        grads = {'dW': dW}
        if self.use_bias:  # tied biases
            grads['db'] = np.sum(dZ, axis=(0, 1, 2), keepdims=True)

        # dX
        padded_dX = np.zeros_like(self._padded)  # [n, h, w, c]
        s0, s1, k0, k1 = self.strides + self.kernel_size
        t_flt = self.W.transpose((3, 1, 2, 0))  # [c, fh, hw, out] => [out, fh, fw, c]
        for i in range(dZ.shape[1]):
            for j in range(dZ.shape[2]):
                padded_dX[:, i * s0:i * s0 + k0, j * s1:j * s1 + k1, :] += dZ[:, i, j, :].reshape(
                    (-1, self.out_channels)).dot(
                    t_flt.reshape((self.out_channels, -1))).reshape((-1, k0, k1, padded_dX.shape[-1]))
        t, b, l, r = [self._p_tblr[0], padded_dX.shape[1] - self._p_tblr[1],
                      self._p_tblr[2], padded_dX.shape[2] - self._p_tblr[3]]
        dX = padded_dX[:, t:b, l:r, :]

        return dX, grads


class Pool(Layer):
    def __init__(self, kernel_size=(3, 3), strides=(1, 1), padding='valid', channels_last=True):
        self.kernel_size = kernel_size
        self.strides = strides
        self.padding = padding.lower()
        if padding not in ('valid', 'same'):
            ValueError('unknown padding type {}'.format(padding))
        self.channels_last = channels_last

    def agg_func(self, x):
        raise NotImplementedError

    def forward(self, X):
        self._X = X
        if not self.channels_last:  # channels_first
            # [batch, channel, height, width] => [batch, height, width, channel]
            self._X = np.transpose(self._X, (0, 2, 3, 1))
        # padded dim from top, bottom, left, right
        self._padded, out, self._p_tblr = get_padded_and_tmp_out(
            self._X, self.kernel_size, self.strides, self._X.shape[-1], self.padding)
        s0, s1, k0, k1 = self.strides + self.kernel_size
        for i in range(0, out.shape[1]):  # in each row of the convoluted feature map
            for j in range(0, out.shape[2]):  # in each column of the convoluted feature map
                window = self._padded[:, i * s0:i * s0 + k0, j * s1:j * s1 + k1, :]  # [n,h,w,c]
                out[:, i, j, :] = self.agg_func(window)
        return out if self.channels_last else out.transpose((0, 3, 1, 2))


class MaxPool2D(Pool):
    def __init__(self, pool_size=(3, 3), strides=(1, 1), padding='valid', channels_last=True):
        super().__init__(pool_size, strides, padding, channels_last)

    def agg_func(self, x):
        return x.max(axis=(1, 2))

    def backward(self, delta):
        s0, s1, k0, k1 = self.strides + self.kernel_size
        padded_dX = np.zeros_like(self._padded)  # [n, h, w, c]
        for i in range(delta.shape[1]):
            for j in range(delta.shape[2]):
                window = self._padded[:, i * s0:i * s0 + k0, j * s1:j * s1 + k1, :]  # [n,fh,fw,c]
                window_mask = window == np.max(window, axis=(1, 2), keepdims=True)
                window_dZ = delta[:, i:i + 1, j:j + 1, :] * window_mask.astype(np.float32)
                padded_dX[:, i * s0:i * s0 + k0, j * s1:j * s1 + k1, :] += window_dZ
        t, b, l, r = [self._p_tblr[0], padded_dX.shape[1] - self._p_tblr[1],
                      self._p_tblr[2], padded_dX.shape[2] - self._p_tblr[3]]
        dX = padded_dX[:, t:b, l:r, :]
        return dX


class AvgPool2D(Pool):
    def __init__(self, kernel_size=(3, 3), strides=(1, 1), padding='valid', channels_last=True):
        super().__init__(kernel_size, strides, padding, channels_last)

    def agg_func(self, x):
        return x.mean(axis=(1, 2))

    def backward(self, delta):
        s0, s1, k0, k1 = self.strides + self.kernel_size
        padded_dX = np.zeros_like(self._padded)  # [n, h, w, c]
        for i in range(delta.shape[1]):
            for j in range(delta.shape[2]):
                window_dZ = delta[:, i:i + 1, j:j + 1, :] * np.full(
                    (1, k0, k1, delta.shape[-1]), 1. / (k0 * k1), dtype=np.float32)
                padded_dX[:, i * s0:i * s0 + k0, j * s1:j * s1 + k1, :] += window_dZ
        t, b, l, r = [self._p_tblr[0], padded_dX.shape[1] - self._p_tblr[1],
                      self._p_tblr[2], padded_dX.shape[2] - self._p_tblr[3]]
        dX = padded_dX[:, t:b, l:r, :]
        return dX


class Flatten(Layer):

    def forward(self, X):
        self._X = X
        return self._X.reshape((self._X.shape[0], -1))

    def backward(self, delta):
        dX = delta.reshape(self._X.shape)
        return dX


class Dropout(Layer):

    def __init__(self, p=0.5):
        self.prob = p
        self.params = []

    def forward(self, X):
        self.mask = np.random.binomial(n=1., p=1. - self.prob, size=X.shape)
        return (X * self.mask).reshape(X.shape)

    def backward(self, delta):
        dX = delta * self.mask
        return dX


def get_padded_and_tmp_out(img, kernel_size, strides, out_channels, padding):
    batch, h, w = img.shape[:3]
    (fh, fw), (sh, sw) = kernel_size, strides

    if padding == 'same':
        out_h = int(np.ceil(h / sh))
        out_w = int(np.ceil(w / sw))
        ph = int(np.max([0, (out_h - 1) * sh + fh - h]))
        pw = int(np.max([0, (out_w - 1) * sw + fw - w]))
        pt, pl = int(np.floor(ph / 2)), int(np.floor(pw / 2))
        pb, pr = ph - pt, pw - pl
    else:  # valid
        out_h = int(np.ceil((h - fh + 1) / sh))
        out_w = int(np.ceil((w - fw + 1) / sw))
        pt, pb, pl, pr = 0, 0, 0, 0
    padded_img = np.pad(img, ((0, 0), (pt, pb), (pl, pr), (0, 0)), 'constant', constant_values=0.).astype(np.float32)
    tmp_out = np.zeros((batch, out_h, out_w, out_channels), dtype=np.float32)
    return padded_img, tmp_out, (pt, pb, pl, pr)
