class Frozen(Harness):

    def test_stack(self, device):
        for dtype in (torch.half, torch.double, torch.int):
            x = torch.randint(low=-100, high=100, size=(2, 3, 4), device=device, dtype=dtype)
            y = torch.randint(low=-100, high=100, size=(2, 3, 4), device=device, dtype=dtype)
            z = torch.randint(low=-100, high=100, size=(2, 3, 4), device=device, dtype=dtype)
            for dim in range(4):
                res = torch.stack((x, y, z), dim)
                res_neg = torch.stack((x, y, z), dim - 4)
                expected_size = x.size()[:dim] + (3,) + x.size()[dim:]
                self.assertEqual(res, res_neg)
                self.assertEqual(res.size(), expected_size)
                self.assertEqual(res.select(dim, 0), x, atol=0, rtol=0)
                self.assertEqual(res.select(dim, 1), y, atol=0, rtol=0)
                self.assertEqual(res.select(dim, 2), z, atol=0, rtol=0)
