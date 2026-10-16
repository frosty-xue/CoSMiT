def pytorch_call(x, axis=0, exclusive=False, reverse=False):
    original_dtype = x.dtype
    if original_dtype == torch.float16:
        x = x.to(torch.float32)
    if exclusive:
        cumsum = torch.cumsum(x, dim=axis) - x
    else:
        cumsum = torch.cumsum(x, dim=axis)
    if reverse:
        cumsum = torch.cumsum(torch.flip(x, dims=[axis]), dim=axis)
        if exclusive:
            cumsum = cumsum - torch.flip(x, dims=[axis])
        cumsum = torch.flip(cumsum, dims=[axis])
    return cumsum.to(original_dtype)