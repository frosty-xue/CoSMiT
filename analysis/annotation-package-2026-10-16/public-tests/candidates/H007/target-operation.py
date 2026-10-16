def pytorch_call(input_tensor, axis=None, keepdims=False):
    return torch.prod(input_tensor, dim=axis, keepdim=keepdims)