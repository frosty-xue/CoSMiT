@handle_frontend_test(
    fn_tree="torch.abs",
    aliases=["torch.absolute"],
    dtype_and_x=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("numeric", full=False).filter(
            lambda x: "uint8" not in x[0]
            and "int8" not in x[0]
            and "uint16" not in x[0]
            and "int16" not in x[0]
            and "float16" not in x[0]
            and "bfloat16" not in x[0]
        ),
        large_abs_safety_factor=2.5,
        small_abs_safety_factor=2.5,
        safety_factor_scale="log",
    ),
)
def test_torch_abs(
    *,
    dtype_and_x,
    on_device,
    fn_tree,
    frontend,
    test_flags,
    backend_fw,
):
    input_dtype, x = dtype_and_x
    helpers.test_frontend_function(
        input_dtypes=input_dtype,
        backend_to_test=backend_fw,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        input=x[0],
    )
