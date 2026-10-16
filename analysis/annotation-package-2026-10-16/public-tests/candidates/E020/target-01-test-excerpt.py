@handle_frontend_method(
    class_tree=CLASS_TREE,
    init_tree="torch.tensor",
    method_name="permute",
    dtype_values_axis=_array_idxes_n_dtype(
        available_dtypes=helpers.get_dtypes("float"),
    ),
)
def test_torch_permute(
    dtype_values_axis,
    frontend_method_data,
    init_flags,
    method_flags,
    frontend,
    on_device,
    backend_fw,
):
    x, idxes, dtype = dtype_values_axis
    unpack_dims = True
    if unpack_dims:
        method_flags.num_positional_args = len(idxes) + 1
        dims = {}
        i = 0
        for x_ in idxes:
            dims[f"x{i}"] = x_
            i += 1
    else:
        dims = {
            "dims": tuple(idxes),
        }
    helpers.test_frontend_method(
        init_input_dtypes=dtype,
        backend_to_test=backend_fw,
        init_all_as_kwargs_np={
            "data": x[0],
        },
        method_input_dtypes=dtype,
        method_all_as_kwargs_np=dims,
        frontend_method_data=frontend_method_data,
        init_flags=init_flags,
        method_flags=method_flags,
        frontend=frontend,
        on_device=on_device,
    )
