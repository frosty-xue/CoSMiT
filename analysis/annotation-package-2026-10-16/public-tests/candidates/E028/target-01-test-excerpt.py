@handle_frontend_test(
    fn_tree="torch.stack",
    dtype_value_shape=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("float"),
        num_arrays=st.shared(helpers.ints(min_value=2, max_value=4), key="num_arrays"),
        shape=st.shared(helpers.get_shape(min_num_dims=1), key="shape"),
    ),
    dim=helpers.get_axis(
        shape=st.shared(helpers.get_shape(min_num_dims=1), key="shape"),
    ).filter(lambda axis: isinstance(axis, int)),
    use_axis_arg=st.booleans(),
)
def test_torch_stack(
    *,
    dtype_value_shape,
    dim,
    use_axis_arg,
    on_device,
    fn_tree,
    frontend,
    test_flags,
    backend_fw,
):
    input_dtype, value = dtype_value_shape
    dim_arg = {"axis" if use_axis_arg else "dim": dim}
    helpers.test_frontend_function(
        input_dtypes=input_dtype,
        backend_to_test=backend_fw,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        tensors=value,
        **dim_arg,
    )
