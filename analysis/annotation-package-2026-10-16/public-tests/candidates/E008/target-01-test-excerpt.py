@handle_frontend_test(
    fn_tree="torch.div",
    aliases=["torch.divide"],
    dtype_and_x=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("numeric"),
        num_arrays=2,
        large_abs_safety_factor=2.5,
        small_abs_safety_factor=2.5,
        safety_factor_scale="log",
    ),
    rounding_mode=st.sampled_from(["floor", "trunc"]) | st.none(),
)
def test_torch_div(
    *,
    dtype_and_x,
    rounding_mode,
    on_device,
    fn_tree,
    frontend,
    test_flags,
    backend_fw,
):
    input_dtype, x = dtype_and_x
    assume(not np.any(np.isclose(x[1], 0)))

    # Absolute tolerance is 1,
    # due to flooring can cause absolute error of 1 due to precision
    helpers.test_frontend_function(
        input_dtypes=input_dtype,
        backend_to_test=backend_fw,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        atol=1,
        input=x[0],
        other=x[1],
        rounding_mode=rounding_mode,
    )
