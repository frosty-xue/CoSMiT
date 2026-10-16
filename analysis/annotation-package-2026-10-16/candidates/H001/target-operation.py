def tensorflow_call(input, dim, keepdim=False):
    if input.shape.ndims == 0:
        return tf.identity(input)
    return tf.reduce_prod(input, axis=dim, keepdims=keepdim)