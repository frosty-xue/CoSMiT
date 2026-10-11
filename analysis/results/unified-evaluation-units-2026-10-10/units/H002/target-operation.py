def tensorflow_call(input, other):
    if input.ndim == 1:
        input = tf.expand_dims(input, axis=0)
    if other.ndim == 1:
        other = tf.expand_dims(other, axis=-1)
    return tf.matmul(input, other)