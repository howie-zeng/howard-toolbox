from __future__ import annotations

from collections.abc import Iterable

import numpy as np

Array = np.ndarray
Parameter = tuple[Array, Array]


class Linear:
    def __init__(
        self,
        in_features: int,
        out_features: int,
        rng: np.random.Generator,
        weight_scale: float = 0.1,
    ) -> None:
        self.weight = rng.normal(loc=0.0, scale=weight_scale, size=(in_features, out_features))
        self.bias = np.zeros(out_features)
        self.grad_weight = np.zeros_like(self.weight)
        self.grad_bias = np.zeros_like(self.bias)
        self._x: Array | None = None

    def forward(self, x: Array) -> Array:
        self._x = x
        return x @ self.weight + self.bias

    def backward(self, grad_out: Array) -> Array:
        if self._x is None:
            raise ValueError("Linear.backward() called before forward().")

        self.grad_weight[...] = self._x.T @ grad_out
        self.grad_bias[...] = grad_out.sum(axis=0)
        return grad_out @ self.weight.T

    def parameters(self) -> list[Parameter]:
        return [(self.weight, self.grad_weight), (self.bias, self.grad_bias)]


class ReLU:
    def __init__(self) -> None:
        self._x: Array | None = None

    def forward(self, x: Array) -> Array:
        self._x = x
        return np.maximum(x, 0.0)

    def backward(self, grad_out: Array) -> Array:
        if self._x is None:
            raise ValueError("ReLU.backward() called before forward().")

        return grad_out * (self._x > 0.0)


class SoftmaxCrossEntropy:
    def __init__(self) -> None:
        self.probs: Array | None = None
        self.labels: Array | None = None

    def forward(self, logits: Array, labels: Array) -> float:
        self.labels = labels

        shifted_logits = logits - logits.max(axis=1, keepdims=True)
        exp_scores = np.exp(shifted_logits)
        self.probs = exp_scores / exp_scores.sum(axis=1, keepdims=True)

        batch_indices = np.arange(logits.shape[0])
        correct_class_probs = self.probs[batch_indices, labels]
        return float(-np.log(correct_class_probs).mean())

    def backward(self) -> Array:
        if self.probs is None or self.labels is None:
            raise ValueError("SoftmaxCrossEntropy.backward() called before forward().")

        grad_logits = self.probs.copy()
        batch_indices = np.arange(grad_logits.shape[0])
        grad_logits[batch_indices, self.labels] -= 1.0
        return grad_logits / grad_logits.shape[0]


class MLP:
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        output_dim: int,
        rng: np.random.Generator,
        weight_scale: float = 0.1,
    ) -> None:
        self.fc1 = Linear(input_dim, hidden_dim, rng, weight_scale)
        self.relu = ReLU()
        self.fc2 = Linear(hidden_dim, output_dim, rng, weight_scale)

    def forward(self, x: Array) -> Array:
        hidden = self.fc1.forward(x)
        activated = self.relu.forward(hidden)
        return self.fc2.forward(activated)

    def backward(self, grad_logits: Array) -> Array:
        grad_hidden = self.fc2.backward(grad_logits)
        grad_hidden_pre_activation = self.relu.backward(grad_hidden)
        return self.fc1.backward(grad_hidden_pre_activation)

    def parameters(self) -> list[Parameter]:
        return [*self.fc1.parameters(), *self.fc2.parameters()]

    def predict(self, x: Array) -> Array:
        return self.forward(x).argmax(axis=1)


class SGD:
    def __init__(self, parameters: Iterable[Parameter], lr: float) -> None:
        self.parameters = list(parameters)
        self.lr = lr

    def step(self) -> None:
        for param, grad in self.parameters:
            param -= self.lr * grad


def make_moons_like(n_samples: int, noise: float, rng: np.random.Generator) -> tuple[Array, Array]:
    n_top = n_samples // 2
    n_bottom = n_samples - n_top

    top_angles = rng.uniform(0.0, np.pi, size=n_top)
    bottom_angles = rng.uniform(0.0, np.pi, size=n_bottom)

    top = np.column_stack([np.cos(top_angles), np.sin(top_angles)])
    bottom = np.column_stack([1.0 - np.cos(bottom_angles), 0.5 - np.sin(bottom_angles)])

    x = np.vstack([top, bottom])
    y = np.concatenate([np.zeros(n_top, dtype=int), np.ones(n_bottom, dtype=int)])

    x += rng.normal(loc=0.0, scale=noise, size=x.shape)

    order = rng.permutation(n_samples)
    return x[order], y[order]
