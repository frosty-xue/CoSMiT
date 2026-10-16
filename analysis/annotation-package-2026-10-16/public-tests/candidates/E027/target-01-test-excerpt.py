@handle_frontend_test(
    fn_tree="tensorflow.stack",
    dtype_values_axis=helpers.dtype_values_axis(
        available_dtypes=helpers.get_dtypes("float"),
        num_arrays=st.shared(helpers.ints(min_value=2, max_value=4), key="num_arrays"),
        shape=helpers.get_shape(min_num_dims=1),
        shared_dtype=True,
        valid_axis=True,
        allow_neg_axes=True,
        force_int_axis=True,
    ),
)
def test_tensorflow_stack(
    dtype_values_axis,
    on_device,
    fn_tree,
    frontend,
    backend_fw,
    test_flags,
):
    input_dtype, values, axis = dtype_values_axis
    helpers.test_frontend_function(
        input_dtypes=input_dtype,
        frontend=frontend,
        backend_to_test=backend_fw,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        values=values,
        axis=axis,
    )
