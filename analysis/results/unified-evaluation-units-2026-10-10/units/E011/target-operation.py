def tensorflow_call(input, other):
    other = tf.cast(other, input.dtype)
    return tf.minimum(input, other)