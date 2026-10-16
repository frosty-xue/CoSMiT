@handle_frontend_test(
    fn_tree="tensorflow.linalg.det",
    dtype_and_input=_get_dtype_and_matrix(),
    test_with_out=st.just(False),
)
def test_tensorflow_det(
    *,
    dtype_and_input,
    frontend,
    backend_fw,
    test_flags,
    fn_tree,
    on_device,
):
    input_dtype, x = dtype_and_input
    helpers.test_frontend_function(
        input_dtypes=input_dtype,
        frontend=frontend,
        test_flags=test_flags,
        backend_to_test=backend_fw,
        fn_tree=fn_tree,
        on_device=on_device,
        input=x[0],
    )
