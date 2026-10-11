def tensorflow_call(input, min=None, max=None):
    min = tf.cast(min, input.dtype)
    max = tf.cast(max, input.dtype)
    clipped = tf.where(input < min, min, input)
    clipped = tf.where(clipped > max, max, clipped)
    return clipped