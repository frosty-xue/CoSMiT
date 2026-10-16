@test_util.run_deprecated_v1
def testFloatBasic(self):
  x = np.arange(-3, 3).reshape(1, 3, 2).astype(np.float32)
  w = x - x.min() + 1.02  # all greater than 1
  y = (x + .5).astype(np.float32)  # no zero
  z = (x + 15.5).astype(np.float32)  # all positive
  k = np.arange(-0.90, 0.90, 0.25).astype(np.float32)  # between -1 and 1

  self._compareBoth(x, np.abs, math_ops.abs)
  self._compareBoth(x, np.abs, _ABS)
  self._compareBoth(x, np.negative, math_ops.negative)
  self._compareBoth(x, np.negative, _NEG)
  self._compareBoth(y, self._inv, math_ops.reciprocal)
  self._compareBoth(x, np.square, math_ops.square)
  self._compareBoth(z, np.sqrt, math_ops.sqrt)
  self._compareBoth(z, self._rsqrt, math_ops.rsqrt)
  self._compareBoth(x, np.exp, math_ops.exp)
  self._compareBoth(x, np.expm1, math_ops.expm1)
  self._compareBoth(z, np.log, math_ops.log)
  self._compareBoth(z, np.log1p, math_ops.log1p)
  self._compareBoth(x, np.sinh, math_ops.sinh)
  self._compareBoth(x, np.cosh, math_ops.cosh)
  self._compareBoth(x, np.tanh, math_ops.tanh)
  self._compareBoth(x, np.arcsinh, math_ops.asinh)
  self._compareBoth(w, np.arccosh, math_ops.acosh)
  self._compareBoth(k, np.arctanh, math_ops.atanh)
  self._compareBoth(x, self._sigmoid, math_ops.sigmoid)
  self._compareBoth(x, self._log_sigmoid, math_ops.log_sigmoid)
  self._compareBoth(y, np.sign, math_ops.sign)
  self._compareBoth(x, np.sin, math_ops.sin)
  self._compareBoth(x, np.cos, math_ops.cos)
  self._compareBoth(k, np.arcsin, math_ops.asin)
  self._compareBoth(k, np.arccos, math_ops.acos)
  self._compareBoth(x, np.arctan, math_ops.atan)
  self._compareBoth(x, np.tan, math_ops.tan)
  self._compareBoth(
      y, np.vectorize(self._replace_domain_error_with_inf(math.lgamma)),
      math_ops.lgamma)
  self._compareBoth(x, np.vectorize(math.erf), math_ops.erf)
  self._compareBoth(x, np.vectorize(math.erfc), math_ops.erfc)
  try:
    from scipy import special  # pylint: disable=g-import-not-at-top
    self._compareBoth(x, special.i0e, special_math_ops.bessel_i0e)
    self._compareBoth(x, special.i1e, special_math_ops.bessel_i1e)
  except ImportError as e:
    tf_logging.warn("Cannot test special functions: %s" % str(e))

  self._compareBothSparse(x, np.abs, math_ops.abs)
  self._compareBothSparse(x, np.negative, math_ops.negative)
  self._compareBothSparse(x, np.square, math_ops.square)
  self._compareBothSparse(z, np.sqrt, math_ops.sqrt, tol=1e-3)
  self._compareBothSparse(x, np.tanh, math_ops.tanh)
  self._compareBothSparse(y, np.sign, math_ops.sign)
  self._compareBothSparse(x, np.vectorize(math.erf), math_ops.erf)
