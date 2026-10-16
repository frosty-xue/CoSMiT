class Frozen(Harness):

    def testTranspose2DAuto(self):
        x_np = [[1, 2, 3], [4, 5, 6]]
        for use_gpu in [False, True]:
            with self.subTest(use_gpu=use_gpu):
                with self.cached_session(use_gpu=use_gpu):
                    x_tf = _operation(x_np)
                    self.assertAllEqual(x_tf, [[1, 4], [2, 5], [3, 6]])
