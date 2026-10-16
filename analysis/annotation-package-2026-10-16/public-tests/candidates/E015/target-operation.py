def tensorflow_call(input, other):
    input = tf.cast(input, other.dtype)
    return tf.atan2(input, other)