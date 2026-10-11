def tensorflow_call(input, dim0, dim1):
    num_dims = len(input.shape)
    if dim0 < 0:
        dim0 += num_dims
    if dim1 < 0:
        dim1 += num_dims
    perm = list(range(num_dims))
    (perm[dim0], perm[dim1]) = (perm[dim1], perm[dim0])
    return tf.transpose(input, perm=perm)