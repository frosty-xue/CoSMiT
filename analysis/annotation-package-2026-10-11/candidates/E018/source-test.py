class Frozen(Harness):

    def _testReshape(self, x, y, use_gpu=False):
        with self.cached_session(use_gpu=use_gpu):
            np_ans = x.reshape(y)
            tf_ans = array_ops.reshape(x, y)
            out = self.evaluate(tf_ans)
            self.assertEqual(tf_ans.get_shape(), out.shape)
            self.assertShapeEqual(np_ans, tf_ans)
            y64 = constant_op.constant(y, dtype=dtypes.int64)
            tf_ans = array_ops.reshape(x, y64)
            out = self.evaluate(tf_ans)
            self.assertEqual(tf_ans.get_shape(), out.shape)
            self.assertShapeEqual(np_ans, tf_ans)

    def _testBothReshape(self, x, y):
        self._testReshape(x, y, False)
        self._testReshape(x, y, True)

    def testFloatBasic(self):
        x = np.arange(1.0, 7.0).reshape([1, 6]).astype(np.float32)
        self._testBothReshape(x, [2, 3])
