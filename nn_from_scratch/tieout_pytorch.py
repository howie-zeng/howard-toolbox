from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

import numpy as np

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from nn_from_scratch.nn_numpy import MLP, SGD, SoftmaxCrossEntropy


class PyTorchUnavailableError(RuntimeError):
    pass


def _import_torch():
    try:
        import torch
    except ModuleNotFoundError:
        raise PyTorchUnavailableError(
            "PyTorch is not installed. Install it to run this tie-out, for example:\n"
            "  python -m pip install torch\n\n"
            "The NumPy implementation and tests do not require PyTorch."
        ) from None

    return torch


def _copy_numpy_weights_to_torch(torch_model, numpy_model: MLP) -> None:
    torch = _import_torch()

    with torch.no_grad():
        torch_model[0].weight.copy_(torch.tensor(numpy_model.fc1.weight.T))
        torch_model[0].bias.copy_(torch.tensor(numpy_model.fc1.bias))
        torch_model[2].weight.copy_(torch.tensor(numpy_model.fc2.weight.T))
        torch_model[2].bias.copy_(torch.tensor(numpy_model.fc2.bias))


def _max_abs_diff(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.max(np.abs(left - right)))


def _print_diff(name: str, left: np.ndarray | float, right: np.ndarray | float) -> None:
    left_arr = np.asarray(left)
    right_arr = np.asarray(right)
    print(f"{name:<30} max abs diff = {_max_abs_diff(left_arr, right_arr):.12g}")


def run_tieout() -> dict[str, float]:
    try:
        torch = _import_torch()
    except PyTorchUnavailableError as exc:
        print(exc)
        return {}

    torch.set_default_dtype(torch.float64)

    rng = np.random.default_rng(42)
    x = rng.normal(size=(5, 3))
    labels = np.array([0, 2, 1, 2, 0])
    lr = 0.05

    numpy_model = MLP(input_dim=3, hidden_dim=4, output_dim=3, rng=np.random.default_rng(123), weight_scale=0.2)
    numpy_loss = SoftmaxCrossEntropy()

    torch_model = torch.nn.Sequential(
        torch.nn.Linear(3, 4),
        torch.nn.ReLU(),
        torch.nn.Linear(4, 3),
    )
    _copy_numpy_weights_to_torch(torch_model, numpy_model)

    x_torch = torch.tensor(x)
    labels_torch = torch.tensor(labels, dtype=torch.long)

    numpy_logits = numpy_model.forward(x)
    numpy_loss_value = numpy_loss.forward(numpy_logits, labels)
    numpy_model.backward(numpy_loss.backward())

    torch_logits = torch_model(x_torch)
    torch_loss = torch.nn.functional.cross_entropy(torch_logits, labels_torch)
    torch_loss.backward()

    diffs = {
        "logits": _max_abs_diff(numpy_logits, torch_logits.detach().numpy()),
        "loss": abs(numpy_loss_value - float(torch_loss.detach().numpy())),
        "fc1.weight.grad": _max_abs_diff(numpy_model.fc1.grad_weight, torch_model[0].weight.grad.detach().numpy().T),
        "fc1.bias.grad": _max_abs_diff(numpy_model.fc1.grad_bias, torch_model[0].bias.grad.detach().numpy()),
        "fc2.weight.grad": _max_abs_diff(numpy_model.fc2.grad_weight, torch_model[2].weight.grad.detach().numpy().T),
        "fc2.bias.grad": _max_abs_diff(numpy_model.fc2.grad_bias, torch_model[2].bias.grad.detach().numpy()),
    }

    numpy_params_before = [param.copy() for param, _ in numpy_model.parameters()]
    torch_params_before = [param.detach().numpy().copy() for param in torch_model.parameters()]

    SGD(numpy_model.parameters(), lr=lr).step()
    torch_optimizer = torch.optim.SGD(torch_model.parameters(), lr=lr)
    torch_optimizer.step()

    numpy_params_after = [param for param, _ in numpy_model.parameters()]
    torch_params_after = _torch_params_in_numpy_layout(torch_params_before, torch_model)

    for idx, (numpy_param, torch_param) in enumerate(zip(numpy_params_after, torch_params_after, strict=True)):
        diffs[f"param{idx}.after_sgd"] = _max_abs_diff(numpy_param, torch_param)

    print("Neural Network From Scratch vs PyTorch Tie-Out")
    print("=" * 52)
    _print_diff("logits", numpy_logits, torch_logits.detach().numpy())
    _print_diff("loss", numpy_loss_value, float(torch_loss.detach().numpy()))
    _print_diff("fc1.weight.grad", numpy_model.fc1.grad_weight, torch_model[0].weight.grad.detach().numpy().T)
    _print_diff("fc1.bias.grad", numpy_model.fc1.grad_bias, torch_model[0].bias.grad.detach().numpy())
    _print_diff("fc2.weight.grad", numpy_model.fc2.grad_weight, torch_model[2].weight.grad.detach().numpy().T)
    _print_diff("fc2.bias.grad", numpy_model.fc2.grad_bias, torch_model[2].bias.grad.detach().numpy())
    for idx, (before, after, torch_after) in enumerate(
        zip(numpy_params_before, numpy_params_after, torch_params_after, strict=True)
    ):
        _print_diff(f"param{idx}.after_sgd", after, torch_after)
        assert before.shape == after.shape

    max_diff = max(diffs.values())
    print("=" * 52)
    print(f"largest difference: {max_diff:.12g}")
    return diffs


def _torch_params_in_numpy_layout(torch_params_before: Sequence[np.ndarray], torch_model) -> list[np.ndarray]:
    torch_params_after = [param.detach().numpy().copy() for param in torch_model.parameters()]

    assert torch_params_before[0].shape == torch_params_after[0].shape
    return [
        torch_params_after[0].T,
        torch_params_after[1],
        torch_params_after[2].T,
        torch_params_after[3],
    ]


if __name__ == "__main__":
    run_tieout()
