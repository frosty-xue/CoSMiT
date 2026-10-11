def tensorflow_call(x,axis=0,exclusive=False,reverse=False):
  return tf.math.cumprod(x,axis,exclusive,reverse)