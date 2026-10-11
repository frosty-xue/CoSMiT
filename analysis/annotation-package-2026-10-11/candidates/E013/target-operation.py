def tensorflow_call(input, exponent):
    exponent = tf.cast(exponent, input.dtype)
    return tf.pow(input, exponent)