@handle_frontend_test(
    fn_tree="tensorflow.reshape",
    input_x_shape=_reshape_helper(),
    test_with_out=st.just(False),
)
def test_tensorflow_reshape(
    *,
    input_x_shape,
    on_device,
    fn_tree,
    backend_fw,
    frontend,
    test_flags,
):
    x, x_dtype, shape = input_x_shape
    helpers.test_frontend_function(
        input_dtypes=x_dtype,
        frontend=frontend,
        backend_to_test=backend_fw,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        tensor=x,
        shape=shape,
    )
