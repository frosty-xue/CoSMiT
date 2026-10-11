class Frozen(Harness):

    def testConcatTuple(self):
        c1 = np.random.rand(4, 4)
        c2 = np.random.rand(4, 4)
        concat_list_t = array_ops.concat([c1, c2], 0)
        concat_tuple_t = array_ops.concat((c1, c2), 0)
        self.assertAllEqual(self.evaluate(concat_list_t), self.evaluate(concat_tuple_t))
