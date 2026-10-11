class Frozen(Harness):

    def test_transposes(self, device, dtype):
        for op in ('T', 'H', 'mT', 'mH', 'adjoint'):
            shapes = ((2, 3), (2, 3, 4)) if op[0] == 'm' or op == 'adjoint' else ((2, 3),)
            for shape in shapes:
                a = make_tensor(shape, device=device, dtype=dtype)
                t1 = getattr(a, op)
                if op == 'adjoint':
                    t1 = t1()
                t2 = a
                t2 = t2.transpose(-2, -1)
                if op[-1] == 'H' or op == 'adjoint':
                    t2 = t2.conj()
                self.assertEqual(t2, t1)
