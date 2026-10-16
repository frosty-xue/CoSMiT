@coalescedonoff
@dtypes(torch.float16, torch.bfloat16, torch.float64, torch.int, torch.cfloat, torch.cdouble)
def test_to_sparse(self, device, dtype, coalesced):
    shape = [5, 2, 10, 4]
    max_nnz = 1
    for value_type in [torch.double, torch.cdouble]:
        for dim, dim_sz in enumerate(shape, 1):
            max_nnz *= dim_sz
            rnnz = torch.randint(2, max_nnz, (1,)).item()
            for nnz in [0, 1, rnnz]:
                expected, _, _ = self._gen_sparse(dim, nnz, shape, dtype=value_type, device=device,
                                                  coalesced=coalesced)
                expected = expected.to(dtype)

                d = expected.to_dense()
                result = d.to_sparse(dim)
                self.assertEqual(d, result.to_dense())
                self.assertEqual(expected.size(), result.size())
                self.assertEqual(dim, result.sparse_dim())
