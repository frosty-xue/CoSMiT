@handle_frontend_test(
    fn_tree="torch.pow",
    dtype_and_x=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("valid"),
        num_arrays=2,
        min_value=1,
        max_value=7,
        shared_dtype=True,
    ),
)
def test_torch_pow(
    dtype_and_x,
    on_device,
    fn_tree,
    frontend,
    test_flags,
    backend_fw,
):
    input_dtype, x = dtype_and_x
    if "int" in input_dtype[0] and isinstance(x[1], int) and x[1] < 0:
        x[1] = -x[1]
    try:
        helpers.test_frontend_function(
            input_dtypes=input_dtype,
            backend_to_test=backend_fw,
            frontend=frontend,
            test_flags=test_flags,
            fn_tree=fn_tree,
            on_device=on_device,
            input=x[0],
            exponent=x[1],
        )
    except Exception as e:
        if any(
            error_string in str(e)
            for error_string in ["overflow", "too large to convert to"]
        ):
            assume(False)
        else:
            raise
