@handle_frontend_test(
    fn_tree="tensorflow.linalg.matmul",
    dtype_x=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("valid"),
        shape=(3, 3),
        num_arrays=2,
        shared_dtype=True,
        min_value=-1,
        max_value=100,
    ),
    transpose_a=st.booleans(),
    transpose_b=st.booleans(),
    test_with_out=st.just(False),
)
def test_tensorflow_matmul(
    *,
    dtype_x,
    transpose_a,
    transpose_b,
    frontend,
    backend_fw,
    test_flags,
    fn_tree,
    on_device,
):
    input_dtype, x = dtype_x
    helpers.test_frontend_function(
        input_dtypes=input_dtype,
        backend_to_test=backend_fw,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        a=x[0],
        b=x[1],
        transpose_a=transpose_a,
        transpose_b=transpose_b,
    )
