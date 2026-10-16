def tensorflow_call(input, dim):
    return tf.cumsum(input, axis=dim)