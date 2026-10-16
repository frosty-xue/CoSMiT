def pytorch_call(input, axis=None):
    return input.squeeze(dim=axis) if axis is not None else input.squeeze()