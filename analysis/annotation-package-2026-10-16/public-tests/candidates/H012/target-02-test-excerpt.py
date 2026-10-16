@handle_frontend_test(
    fn_tree="torch.ones",
    size=helpers.ints(min_value=1, max_value=3),
    shape=helpers.get_shape(
        allow_none=False,
        min_num_dims=1,
        max_num_dims=5,
        min_dim_size=1,
        max_dim_size=10,
    ),
    dtype=helpers.get_dtypes("numeric", full=False),
)
def test_torch_ones(
    *,
    shape,
    size,
    dtype,
    on_device,
    fn_tree,
    frontend,
    test_flags,
    backend_fw,
):
    dims = {}
    size = (size,)
    if shape is None:
        i = 0
        for x_ in size:
            dims[f"x{i}"] = x_
            i += 1
    helpers.test_frontend_function(
        input_dtypes=dtype,
        backend_to_test=backend_fw,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        **dims,
        size=shape,
        dtype=dtype[0],
        device=on_device,
    )
