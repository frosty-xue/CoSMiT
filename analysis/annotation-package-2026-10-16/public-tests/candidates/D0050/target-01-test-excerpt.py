@onlyCPU
@dtypes(*get_all_math_dtypes("cpu"))
def test_rdiv(self, device, dtype):
    if dtype is torch.float16:
        return
    elif dtype.is_complex:
        x = torch.rand(100, dtype=dtype, device=device).add(1).mul(4)
    else:
        x = torch.rand(100, device=device).add(1).mul(4).to(dtype)
    y = 30 / x
    z = torch.tensor([30 / v.item() for v in x], device=device)
    self.assertEqual(y, z, exact_dtype=False)
