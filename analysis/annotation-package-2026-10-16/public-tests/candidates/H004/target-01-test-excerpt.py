@handle_frontend_test(
    fn_tree="tensorflow.linalg.trace",
    dtype_and_input=_get_dtype_and_matrix(),
    test_with_out=st.just(False),
)
def test_tensorflow_trace(
    dtype_and_input,
    backend_fw,
    frontend,
    test_flags,
    fn_tree,
):
    input_dtype, x = dtype_and_input
    helpers.test_frontend_function(
        input_dtypes=input_dtype,
        backend_to_test=backend_fw,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        x=x[0],
    )
