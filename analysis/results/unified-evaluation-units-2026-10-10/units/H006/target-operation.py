def tensorflow_call(input, dim):
    return tf.math.cumprod(input, axis=dim)