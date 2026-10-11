class Frozen(Harness):

    def assertEqualHelper(self, actual, expected, msg, *, dtype, exact_dtype=True, **kwargs):
        assert isinstance(actual, torch.Tensor)
        if isinstance(expected, Number):
            self.assertEqual(actual.item(), expected, msg=msg, **kwargs)
        elif isinstance(expected, np.ndarray):
            if exact_dtype:
                if expected.dtype == np.float32:
                    assert actual.dtype in (torch.float16, torch.bfloat16, torch.float32)
                else:
                    assert expected.dtype == torch_to_numpy_dtype_dict[actual.dtype]
            self.assertEqual(actual, torch.from_numpy(expected).to(actual.dtype), msg, exact_device=False, **kwargs)
        else:
            self.assertEqual(actual, expected, msg, exact_device=False, **kwargs)

    def _test_reference_numerics(self, dtype, op, gen, equal_nan=True):

        def _helper_reference_numerics(expected, actual, msg, exact_dtype, equal_nan=True):
            if not torch.can_cast(numpy_to_torch_dtype_dict[expected.dtype.type], dtype):
                exact_dtype = False
            if dtype is torch.bfloat16 and expected.dtype == np.float32:
                self.assertEqualHelper(actual, expected, msg, dtype=dtype, exact_dtype=exact_dtype, rtol=0.016, atol=1e-05)
            else:
                self.assertEqualHelper(actual, expected, msg, dtype=dtype, equal_nan=equal_nan, exact_dtype=exact_dtype)
        for sample in gen:
            l = sample.input
            r = sample.args[0]
            numpy_sample = sample.numpy()
            l_numpy = numpy_sample.input
            r_numpy = numpy_sample.args[0]
            actual = op(l, r)
            expected = op.ref(l_numpy, r_numpy)
            if np.__version__ > '2' and op.name in ('sub', '_refs.sub') and isinstance(l_numpy, np.ndarray):
                expected = expected.astype(l_numpy.dtype)

            def _numel(x):
                if isinstance(x, torch.Tensor):
                    return x.numel()
                return 1
            if _numel(l) <= 100 and _numel(r) <= 100:
                msg = f'Failed to produce expected results! Input lhs tensor was {l}, rhs tensor was {r}, torch result is {actual}, and reference result is {expected}.'
            else:
                msg = None
            exact_dtype = True
            if isinstance(actual, torch.Tensor):
                _helper_reference_numerics(expected, actual, msg, exact_dtype, equal_nan)
            else:
                for x, y in zip(expected, actual):
                    _helper_reference_numerics(x, y, msg, exact_dtype, equal_nan)
