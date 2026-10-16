@handle_frontend_test(
    fn_tree="tensorflow.squeeze",
    dtype_value=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("valid"),
        shape=st.shared(helpers.get_shape(), key="value_shape"),
    ),
    axis=_squeeze_helper(),
)
def test_tensorflow_squeeze_general(
    *,
    dtype_value,
    axis,
    on_device,
    backend_fw,
    fn_tree,
    frontend,
    test_flags,
):
    dtype, xs = dtype_value
    helpers.test_frontend_function(
        input_dtypes=dtype,
        frontend=frontend,
        backend_to_test=backend_fw,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        input=xs[0],
        axis=axis,
    )
