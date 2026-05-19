# Neural Network From Scratch

This folder is a small learning scaffold for reviewing neural networks from two angles:

- the math of forward propagation and backpropagation
- the way PyTorch packages the same operations into modules, losses, and optimizers

The from-scratch path uses NumPy only. Softmax and cross-entropy are implemented directly with array operations so the key math is visible.

## Files

- `nn_numpy.py`: minimal NumPy implementation of `Linear`, `ReLU`, `SoftmaxCrossEntropy`, `SGD`, and a small MLP.
- `tieout_pytorch.py`: deterministic tie-out against an equivalent PyTorch model.
- `neural_network_from_scratch.ipynb`: guided walkthrough for concepts, code, tie-outs, and training.

## Suggested Order

1. Read the shape notes in the notebook.
2. Step through the NumPy forward pass.
3. Step through the manual backward pass.
4. Run the PyTorch tie-out and inspect the differences.
5. Train both models on the synthetic classification example.

## What The Tie-Out Proves

`tieout_pytorch.py` compares:

- logits
- cross-entropy loss
- gradients for every weight and bias
- parameters after one SGD update

The expected differences are floating-point noise. Larger differences usually mean a transpose, averaging, or loss-gradient convention is off.

## Running

Run the NumPy tests:

```powershell
python -m pytest tests/test_nn_from_scratch.py
```

Run the PyTorch tie-out:

```powershell
python nn_from_scratch/tieout_pytorch.py
```

If PyTorch is not installed, the tie-out script prints an install hint and exits cleanly.
