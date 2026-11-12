import torch

from nych_language_model.model import DecoderConfig, NYCHDecoder


def test_decoder_forward_loss_and_backward():
    config = DecoderConfig(vocab_size=19, max_seq_len=16)
    model = NYCHDecoder(config)
    input_ids = torch.tensor([[1, 2, 3, 4], [4, 3, 2, 1]], dtype=torch.long)
    labels = torch.tensor([[2, 3, 4, 5], [3, 2, 1, 0]], dtype=torch.long)
    logits, loss = model(input_ids, labels)
    assert logits.shape == (2, 4, 19)
    assert loss is not None and torch.isfinite(loss)
    loss.backward()
    assert model.token_embeddings.weight.grad is not None
    assert torch.isfinite(model.token_embeddings.weight.grad).all()


def test_decoder_is_causal():
    config = DecoderConfig(vocab_size=17, max_seq_len=16, dropout=0.0)
    model = NYCHDecoder(config).eval()
    left = torch.tensor([[1, 2, 3, 4]], dtype=torch.long)
    changed_future = torch.tensor([[1, 2, 9, 8]], dtype=torch.long)
    with torch.no_grad():
        logits_left, _ = model(left)
        logits_changed, _ = model(changed_future)
    torch.testing.assert_close(logits_left[:, :2], logits_changed[:, :2])


def test_v1_non_embedding_parameter_count():
    config = DecoderConfig(vocab_size=11)
    model = NYCHDecoder(config)
    assert config.expected_non_embedding_parameters == 524_928
    assert model.parameter_count() == 11 * 128 + 524_928


def test_sequence_limit_and_label_shape_are_enforced():
    config = DecoderConfig(vocab_size=11, max_seq_len=4)
    model = NYCHDecoder(config)
    with torch.no_grad():
        try:
            model(torch.tensor([[1, 2, 3, 4, 5]], dtype=torch.long))
        except ValueError as exc:
            assert "sequence length" in str(exc)
        else:
            raise AssertionError("too-long sequence was accepted")
    try:
        model(torch.tensor([[1, 2]], dtype=torch.long), torch.tensor([[1]], dtype=torch.long))
    except ValueError as exc:
        assert "same shape" in str(exc)
    else:
        raise AssertionError("mismatched labels were accepted")
