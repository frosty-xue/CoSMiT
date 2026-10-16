@handle_frontend_method(
    class_tree=CLASS_TREE,
    init_tree="torch.tensor",
    method_name="sum",
    dtype_x_dim=_get_castable_dtype(
        min_value=-1e04,
        max_value=1e04,
    ),
    keepdim=st.booleans(),
)
def test_torch_sum(
    dtype_x_dim,
    keepdim,
    frontend_method_data,
    init_flags,
    method_flags,
    frontend,
    on_device,
    backend_fw,
):
    input_dtype, x, dim, castable_dtype = dtype_x_dim
    if method_flags.as_variable:
        castable_dtype = input_dtype
    input_dtype = [input_dtype]
    helpers.test_frontend_method(
        init_input_dtypes=input_dtype,
        backend_to_test=backend_fw,
        init_all_as_kwargs_np={
            "data": x[0],
        },
        method_input_dtypes=input_dtype,
        method_all_as_kwargs_np={
            "dim": dim,
            "keepdim": keepdim,
            "dtype": castable_dtype,
        },
        frontend_method_data=frontend_method_data,
        init_flags=init_flags,
        method_flags=method_flags,
        frontend=frontend,
        on_device=on_device,
        atol_=1e-02,
        rtol_=1e-02,
    )
