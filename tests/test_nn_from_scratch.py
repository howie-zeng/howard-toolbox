import numpy as np

from nn_from_scratch.nn_numpy import MLP, SGD, Linear, ReLU, SoftmaxCrossEntropy, make_moons_like


def test_linear_forward_and_backward_match_hand_calculation() -> None:
    layer = Linear(
        in_features=2,
        out_features=3,
        rng=np.random.default_rng(0),
        weight_scale=1.0,
    )
    layer.weight = np.array([[0.2, -0.4, 0.1], [0.7, 0.3, -0.5]])
    layer.bias = np.array([0.1, -0.2, 0.3])

    x = np.array([[1.0, 2.0], [-1.0, 0.5]])
    upstream = np.array([[0.5, -1.0, 0.25], [1.5, 0.0, -0.75]])

    out = layer.forward(x)
    dx = layer.backward(upstream)

    expected_out = x @ layer.weight + layer.bias
    expected_dw = x.T @ upstream
    expected_db = upstream.sum(axis=0)
    expected_dx = upstream @ layer.weight.T

    np.testing.assert_allclose(out, expected_out)
    np.testing.assert_allclose(layer.grad_weight, expected_dw)
    np.testing.assert_allclose(layer.grad_bias, expected_db)
    np.testing.assert_allclose(dx, expected_dx)


def test_relu_backward_blocks_negative_and_zero_inputs() -> None:
    relu = ReLU()
    x = np.array([[-2.0, 0.0, 3.0], [4.0, -1.0, 0.5]])
    upstream = np.ones_like(x)

    out = relu.forward(x)
    dx = relu.backward(upstream)

    np.testing.assert_array_equal(out, np.array([[0.0, 0.0, 3.0], [4.0, 0.0, 0.5]]))
    np.testing.assert_array_equal(dx, np.array([[0.0, 0.0, 1.0], [1.0, 0.0, 1.0]]))


def test_softmax_cross_entropy_uses_raw_stable_numpy_math() -> None:
    loss_fn = SoftmaxCrossEntropy()
    logits = np.array([[2.0, 1.0, 0.1], [-1.0, 3.0, 0.5]])
    labels = np.array([0, 2])

    loss = loss_fn.forward(logits, labels)
    grad = loss_fn.backward()

    shifted = logits - logits.max(axis=1, keepdims=True)
    exp_scores = np.exp(shifted)
    probs = exp_scores / exp_scores.sum(axis=1, keepdims=True)
    expected_loss = -np.log(probs[np.arange(2), labels]).mean()
    expected_grad = probs.copy()
    expected_grad[np.arange(2), labels] -= 1.0
    expected_grad /= 2

    np.testing.assert_allclose(loss, expected_loss)
    np.testing.assert_allclose(loss_fn.probs, probs)
    np.testing.assert_allclose(grad, expected_grad)


def test_mlp_backward_and_sgd_update_all_parameters() -> None:
    model = MLP(input_dim=2, hidden_dim=4, output_dim=3, rng=np.random.default_rng(1))
    x = np.array([[0.2, -0.5], [1.0, 0.3], [-0.7, 0.8]])
    labels = np.array([0, 2, 1])
    loss_fn = SoftmaxCrossEntropy()

    logits = model.forward(x)
    loss = loss_fn.forward(logits, labels)
    model.backward(loss_fn.backward())

    before = [(param.copy(), grad.copy()) for param, grad in model.parameters()]
    SGD(model.parameters(), lr=0.1).step()

    assert loss > 0
    for (param_before, grad), (param_after, _) in zip(before, model.parameters(), strict=True):
        np.testing.assert_allclose(param_after, param_before - 0.1 * grad)


def test_sgd_created_before_backward_uses_latest_gradients() -> None:
    model = MLP(input_dim=2, hidden_dim=4, output_dim=2, rng=np.random.default_rng(4))
    optimizer = SGD(model.parameters(), lr=0.2)
    loss_fn = SoftmaxCrossEntropy()
    x = np.array([[0.2, -0.5], [1.0, 0.3], [-0.7, 0.8]])
    labels = np.array([0, 1, 1])

    logits = model.forward(x)
    loss_fn.forward(logits, labels)
    model.backward(loss_fn.backward())

    before = [param.copy() for param, _ in model.parameters()]
    expected_after = [param - 0.2 * grad for param, grad in model.parameters()]
    optimizer.step()

    for param_before, expected, (param_after, _) in zip(before, expected_after, model.parameters(), strict=True):
        assert not np.allclose(param_after, param_before)
        np.testing.assert_allclose(param_after, expected)


def test_make_moons_like_is_deterministic_and_binary() -> None:
    x1, y1 = make_moons_like(n_samples=20, noise=0.05, rng=np.random.default_rng(7))
    x2, y2 = make_moons_like(n_samples=20, noise=0.05, rng=np.random.default_rng(7))

    assert x1.shape == (20, 2)
    assert y1.shape == (20,)
    assert set(np.unique(y1)) == {0, 1}
    np.testing.assert_allclose(x1, x2)
    np.testing.assert_array_equal(y1, y2)
