@handle_frontend_test(
    fn_tree="tensorflow.transpose",
    dtype_and_x=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("float"),
        shape=st.shared(helpers.get_shape(min_num_dims=1), key="shape"),
    ),
    perm=_get_perm_helper(),
    conjugate=st.booleans(),
    test_with_out=st.just(False),
)
def test_tensorflow_transpose(
    *,
    dtype_and_x,
    perm,
    conjugate,
    frontend,
    backend_fw,
    test_flags,
    fn_tree,
    on_device,
):
    dtype, x = dtype_and_x
    helpers.test_frontend_function(
        input_dtypes=dtype,
        frontend=frontend,
        backend_to_test=backend_fw,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        a=x[0],
        perm=perm,
        conjugate=conjugate,
    )
