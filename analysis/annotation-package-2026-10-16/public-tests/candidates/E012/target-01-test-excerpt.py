@handle_frontend_test(
    fn_tree="torch.min",
    dtype_input_axis=helpers.dtype_values_axis(
        available_dtypes=helpers.get_dtypes("numeric"),
        min_num_dims=1,
        valid_axis=True,
        force_int_axis=True,
        num_arrays=st.integers(min_value=1, max_value=2),
    ),
    keepdim=st.booleans(),
)
def test_torch_min(
    *,
    dtype_input_axis,
    keepdim,
    on_device,
    fn_tree,
    frontend,
    test_flags,
    backend_fw,
):
    input_dtype, input, axis = dtype_input_axis
    inputs = {f"input{i}": input[i] for i in range(len(input))}
    kwargs = {"dim": axis, "keepdim": keepdim} if len(inputs) == 1 else {}
    test_flags.num_positional_args = len(input)
    helpers.test_frontend_function(
        input_dtypes=input_dtype,
        backend_to_test=backend_fw,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        **inputs,
        **kwargs,
    )
