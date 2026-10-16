def tensorflow_call(input, other):
    input = tf.cast(input, other.dtype)
    return tf.multiply(input, other)