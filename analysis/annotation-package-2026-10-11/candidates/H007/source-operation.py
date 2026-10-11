def tensorflow_call(input_tensor,axis=None,keepdims=False):
  return tf.reduce_prod(input_tensor,axis,keepdims)