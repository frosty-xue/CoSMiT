def pytorch_call(x, axis=0, exclusive=False, reverse=False):
    if exclusive:
        if reverse:
            x = x.flip(dims=[axis])
        cumprod = torch.cumprod(x, dim=axis)
        ones_shape = list(x.shape)
        ones_shape[axis] = 1
        ones_tensor = torch.ones(ones_shape, dtype=x.dtype, device=x.device)
        cumprod = torch.cat((ones_tensor, cumprod[:-1]), dim=axis)
        if reverse:
            cumprod = cumprod.flip(dims=[axis])
        return cumprod
    else:
        if reverse:
            x = x.flip(dims=[axis])
        cumprod = torch.cumprod(x, dim=axis)
        if reverse:
            cumprod = cumprod.flip(dims=[axis])
        return cumprod