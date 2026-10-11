def pytorch_call(a, perm=None, conjugate=False):
    if conjugate:
        a = a.conj()
    return a.permute(*perm)