class Frozen(Harness):

    def randn(self, shape, dtype):
        data = np.random.randn(*shape)
        if dtype == np.bool_:
            return data < 0
        else:
            return data.astype(dtype)

    def testSimple(self):
        np.random.seed(7)
        for shape in ((2,), (3,), (2, 3), (3, 2), (8, 2, 10)):
            rank = len(shape)
            for axis in range(-rank, rank):
                for dtype in [np.bool_, np.float32, np.int32, np.int64, dtypes.float8_e5m2.as_numpy_dtype, dtypes.float8_e4m3fn.as_numpy_dtype]:
                    data = self.randn(shape, dtype)
                    xs = np_split_squeeze(data, axis)
                    with self.subTest(shape=shape, axis=axis, dtype=dtype):
                        c = _operation(xs, axis=axis)
                        self.assertAllEqual(c, data)
