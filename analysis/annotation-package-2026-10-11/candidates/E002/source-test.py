class Frozen(Harness):

    def _compareCpu(self, x, y, np_func, tf_func, also_compare_variables=False):
        np_ans = np_func(x, y)
        with test_util.force_cpu():
            inx = ops.convert_to_tensor(x)
            iny = ops.convert_to_tensor(y)
            out = tf_func(inx, iny)
            tf_cpu = self.evaluate(out)
            np_left = self.evaluate(tf_func(x, iny))
            np_right = self.evaluate(tf_func(inx, y))
            if also_compare_variables:
                var_x = variables.Variable(x)
                var_y = variables.Variable(y)
                self.evaluate(variables.global_variables_initializer())
                print(type(x), type(y), type(var_x), type(var_y))
                print(type(tf_func(x, var_y)), type(tf_func(var_x, y)))
                np_var_left = self.evaluate(tf_func(x, var_y))
                np_var_right = self.evaluate(tf_func(var_x, y))
        if np_ans.dtype != np.object_:
            self.assertAllClose(np_ans, tf_cpu)
            self.assertAllClose(np_ans, np_left)
            self.assertAllClose(np_ans, np_right)
            if also_compare_variables:
                self.assertAllClose(np_ans, np_var_left)
                self.assertAllClose(np_ans, np_var_right)
        self.assertShapeEqual(np_ans, out)
