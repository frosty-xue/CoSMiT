def tensorflow_call(input, dim=None):
    if dim is not None:
        if input.shape[dim] == 1:
            return tf.squeeze(input, axis=dim)
        else:
            return input
    return tf.squeeze(input)