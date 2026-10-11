def tensorflow_call(tensors, dim=0):
    return tf.concat(tensors, axis=dim)