@handle_frontend_test(
    fn_tree="torch.matmul",
    dtype_xy=_get_dtype_and_3dbatch_matrices(),
)
def test_torch_matmul(
    dtype_xy,
    on_device,
    fn_tree,
    frontend,
    test_flags,
    backend_fw,
):
    dtype, x, y = dtype_xy
    helpers.test_frontend_function(
        input_dtypes=dtype,
        backend_to_test=backend_fw,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        rtol=1e-02,
        input=x,
        other=y,
        out=None,
    )
