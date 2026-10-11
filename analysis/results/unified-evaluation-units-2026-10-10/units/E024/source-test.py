class Frozen(Harness):

    def testExpandDimsDimType(self):
        for dtype in [dtypes.int32, dtypes.int64]:
            x = np.zeros([2])
            np_ans = np.expand_dims(x, axis=0)
            with self.cached_session():
                tensor = array_ops.expand_dims(x, constant_op.constant(0, dtype))
                tf_ans = self.evaluate(tensor)
            self.assertShapeEqual(np_ans, tensor)
            self.assertAllEqual(np_ans, tf_ans)
