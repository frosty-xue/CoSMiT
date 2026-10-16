class Frozen(Harness):

    def test_clamp(self, device, dtype):
        test_args = [*product([(100, 50), (10, 64), (97,)], (True, False))]
        for shape, noncontig in test_args:
            x = make_tensor(shape, device=device, dtype=dtype, noncontiguous=noncontig)
            ub = make_tensor(shape, device=device, dtype=dtype, noncontiguous=noncontig)
            lb = make_tensor(shape, device=device, dtype=dtype, noncontiguous=noncontig)
            expect = x.max(lb).min(ub)
            actual = _operation(x, lb, ub)
            self.assertEqual(expect, actual)
            expect = np.clip(x.cpu().numpy(), lb.cpu().numpy(), ub.cpu().numpy())
            self.assertEqual(expect, actual)
            expect = x.max(lb)
            actual = _operation(x, min=lb)
            self.assertEqual(expect, actual)
            expect = x.min(ub)
            actual = _operation(x, max=ub)
            self.assertEqual(expect, actual)
            expect = x.max(lb[0]).min(ub[..., :1])
            actual = _operation(x, lb[0], ub[..., :1])
            self.assertEqual(expect, actual)
            expect = x[..., :1].max(lb).min(ub)
            actual = _operation(x[..., :1], lb, ub)
            self.assertEqual(expect, actual)
