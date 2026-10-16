@handle_frontend_test(
    fn_tree="torch.clamp",
    aliases=["torch.clip"],
    input_and_ranges=_get_clip_inputs(),
)
def test_torch_clamp(
    *,
    input_and_ranges,
    on_device,
    fn_tree,
    frontend,
    test_flags,
    backend_fw,
):
    x_dtype, x, min, max = input_and_ranges
    helpers.test_frontend_function(
        input_dtypes=x_dtype,
        backend_to_test=backend_fw,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        input=x[0],
        min=min,
        max=max,
    )
