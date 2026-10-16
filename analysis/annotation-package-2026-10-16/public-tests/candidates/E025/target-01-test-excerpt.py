@handle_frontend_test(
    fn_tree="tensorflow.concat",
    dtype_input_axis=helpers.dtype_values_axis(
        available_dtypes=helpers.get_dtypes("numeric"),
        num_arrays=st.integers(min_value=1, max_value=4),
        min_num_dims=1,
        valid_axis=True,
        force_int_axis=True,
        shared_dtype=True,
    ),
    test_with_out=st.just(False),
)
def test_tensorflow_concat(
    *,
    dtype_input_axis,
    on_device,
    fn_tree,
    frontend,
    backend_fw,
    test_flags,
):
    input_dtype, x, axis = dtype_input_axis
    helpers.test_frontend_function(
        input_dtypes=input_dtype,
        frontend=frontend,
        backend_to_test=backend_fw,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        values=x,
        axis=axis,
    )
