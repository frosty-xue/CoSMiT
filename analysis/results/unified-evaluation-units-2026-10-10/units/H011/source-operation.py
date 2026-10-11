def tensorflow_call(x,axis=0,exclusive=False,reverse=False):
  return tf.cumsum(x,axis,exclusive,reverse)