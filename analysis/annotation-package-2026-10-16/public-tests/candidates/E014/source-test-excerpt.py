@handle_frontend_test(
    fn_tree="tensorflow.math.pow",
    dtype_and_x=helpers.dtype_and_values(
        available_dtypes=[
            "float16",
            "float32",
            "float64",
            "int32",
            "int64",
        ],
        num_arrays=2,
        min_value=1,
        max_value=7,
        shared_dtype=True,
    ),
    test_with_out=st.just(False),
)
def test_tensorflow_pow(dtype_and_x, frontend, test_flags, backend_fw, fn_tree):
    input_dtype, x = dtype_and_x
    helpers.test_frontend_function(
        input_dtypes=input_dtype,
        backend_to_test=backend_fw,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        x=x[0],
        y=x[1],
    )
