def tensorflow_call(t,clip_value_min,clip_value_max):
  return tf.clip_by_value(t,clip_value_min,clip_value_max)