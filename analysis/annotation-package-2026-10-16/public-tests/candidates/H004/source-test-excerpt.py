@handle_frontend_test(
    fn_tree="torch.trace",
    dtype_and_values=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("numeric"),
        shape=st.shared(helpers.get_shape(min_num_dims=2, max_num_dims=2), key="shape"),
    ),
)
def test_torch_trace(
    *,
    dtype_and_values,
    on_device,
    fn_tree,
    frontend,
    test_flags,
    backend_fw,
):
    dtype, value = dtype_and_values
    helpers.test_frontend_function(
        input_dtypes=dtype,
        backend_to_test=backend_fw,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        input=value[0],
    )
