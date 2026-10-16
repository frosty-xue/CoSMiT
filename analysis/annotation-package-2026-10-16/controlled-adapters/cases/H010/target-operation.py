def pytorch_call(x):
    if x.dim() < 2:
        raise ValueError('Input tensor must be at least 2D.')
    trace = torch.diagonal(x, dim1=-2, dim2=-1).sum(dim=-1)
    if x.dim() > 2:
        return trace.view(trace.size(0), -1)
    else:
        return trace