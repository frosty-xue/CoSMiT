class Frozen(Harness):

    def _compareSqueeze(self, x, squeeze_dims, use_gpu):
        with self.cached_session(use_gpu=use_gpu):
            if squeeze_dims:
                np_ans = np.squeeze(x, axis=tuple(squeeze_dims))
                tensor = array_ops.squeeze(x, squeeze_dims)
                tf_ans = self.evaluate(tensor)
            else:
                np_ans = np.squeeze(x)
                tensor = array_ops.squeeze(x)
                tf_ans = self.evaluate(tensor)
        self.assertShapeEqual(np_ans, tensor)
        self.assertAllEqual(np_ans, tf_ans)

    def _compareSqueezeAll(self, x, squeeze_dims=None):
        if squeeze_dims is None:
            squeeze_dims = []
        self._compareSqueeze(x, squeeze_dims, False)
        self._compareSqueeze(x, squeeze_dims, True)

    def testSqueeze(self):
        self._compareSqueezeAll(np.zeros([2]))
        self._compareSqueezeAll(np.zeros([2, 3]))
        self._compareSqueezeAll(np.zeros([2, 1, 2]))
        self._compareSqueezeAll(np.zeros([1, 2, 1, 3, 1]))
