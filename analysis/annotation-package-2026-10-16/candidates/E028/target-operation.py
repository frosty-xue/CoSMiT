def pytorch_call(values, axis=0):
    return torch.stack(values, dim=axis)