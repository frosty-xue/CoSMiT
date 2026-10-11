def tensorflow_call(tensors, dim=0):
    return tf.stack(tensors, axis=dim)