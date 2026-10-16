def pytorch_call(a, b, transpose_a=False, transpose_b=False, adjoint_a=False, adjoint_b=False, a_is_sparse=False, b_is_sparse=False, output_type=None):
    if transpose_a:
        a = a.t()
    if transpose_b:
        b = b.t()
    if adjoint_a:
        a = a.conj().t()
    if adjoint_b:
        b = b.conj().t()
    if a_is_sparse:
        a = a.to_sparse()
    if b_is_sparse:
        b = b.to_sparse()
    result = torch.matmul(a, b)
    return result