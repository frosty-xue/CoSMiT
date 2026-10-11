class Frozen(Harness):

    def testClipByValue(self):
        with self.session():
            x = constant_op.constant([-5.0, 2.0, 3.0, 4.0, 5.0, 6.0], shape=[2, 3])
            np_ans = [[-4.4, 2.0, 3.0], [4.0, 4.4, 4.4]]
            clip_value = 4.4
            ans = clip_ops.clip_by_value(x, -clip_value, clip_value)
            tf_ans = self.evaluate(ans)
        self.assertAllClose(np_ans, tf_ans)
