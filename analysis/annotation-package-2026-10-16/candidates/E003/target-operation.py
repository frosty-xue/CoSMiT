def tensorflow_call(input, other):
    if input.dtype != other.dtype:
        other = tf.cast(other, input.dtype)
    return tf.subtract(input, other)