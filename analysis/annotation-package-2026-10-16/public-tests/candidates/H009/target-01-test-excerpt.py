@handle_frontend_test(
    fn_tree="torch.linalg.det",
    aliases=["torch.det"],
    dtype_and_x=_get_dtype_and_matrix(square=True, batch=True),
)
def test_torch_det(
    *,
    dtype_and_x,
    on_device,
    fn_tree,
    frontend,
    test_flags,
    backend_fw,
):
    dtype, x = dtype_and_x
    test_flags.num_positional_args = len(x)
    helpers.test_frontend_function(
        input_dtypes=dtype,
        backend_to_test=backend_fw,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        A=x[0],
    )
