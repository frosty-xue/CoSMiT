# Verbatim selected functions from pinned Ivy assertions.py; only test_dtypes=True supported.
import numpy as np

TOLERANCE_DICT = {
    "float16": 1e-2,
    "bfloat16": 1e-2,
    "float32": 1e-5,
    "float64": 1e-5,
    None: 1e-5,
}

def assert_all_close(
    ret_np,
    ret_from_gt_np,
    backend: str,
    rtol=1e-05,
    atol=1e-08,
    ground_truth_backend="TensorFlow",
    test_dtypes=True,
):
    """Match the ret_np and ret_from_gt_np inputs element-by-element to ensure
    that they are the same.

    Parameters
    ----------
    ret_np
        Return from the framework to test. Ivy Container or Numpy Array.
    ret_from_gt_np
        Return from the ground truth framework. Ivy Container or Numpy Array.
    rtol
        Relative Tolerance Value.
    atol
        Absolute Tolerance Value.
    ground_truth_backend
        Ground Truth Backend Framework.
    test_dtypes
        whether to check the dtypes of the return values match.

    Returns
    -------
    None if the test passes, else marks the test as failed.
    """
    if not test_dtypes:
        ret_np, ret_from_gt_np = ivy.promote_types_of_inputs(ret_np, ret_from_gt_np)
    ret_dtype = str(ret_np.dtype)
    ret_from_gt_dtype = str(ret_from_gt_np.dtype).replace("longlong", "int64")
    assert ret_dtype == ret_from_gt_dtype, (
        f"the ground truth framework {ground_truth_backend} returned a"
        f" {ret_from_gt_dtype} datatype while the backend {backend} returned a"
        f" {ret_dtype} datatype"
    )
    # TODO enable
    # if ivy.is_ivy_container(ret_np) and ivy.is_ivy_container(ret_from_gt_np):
    #     ivy.Container.cont_multi_map(assert_all_close, [ret_np, ret_from_gt_np])
    # else:
    if ret_np.dtype == "bfloat16" or ret_from_gt_np.dtype == "bfloat16":
        ret_np = ret_np.astype("float64")
        ret_from_gt_np = ret_from_gt_np.astype("float64")
    assert np.allclose(
        np.nan_to_num(ret_np), np.nan_to_num(ret_from_gt_np), rtol=rtol, atol=atol
    ), (
        f" the results from backend {backend} "
        f"and ground truth framework {ground_truth_backend} "
        f"do not match\n {ret_np}!={ret_from_gt_np} \n\n"
        "The mismatching elements are at `False` indices:\n\n"
        f"{ret_np == ret_from_gt_np} \n\n"
    )

def assert_same_type_and_shape(values, this_key_chain=None):
    x_, y_ = values
    for x, y in zip(x_, y_):
        if isinstance(x, np.ndarray):
            x_d = str(x.dtype).replace("longlong", "int64")
            y_d = str(y.dtype).replace("longlong", "int64")
            assert (
                x.shape == y.shape
            ), f"returned shape = {x.shape}, ground-truth returned shape = {y.shape}"
            assert (
                x_d == y_d
            ), f"returned dtype = {x_d}, ground-truth returned dtype = {y_d}"

def value_test(
    *,
    ret_np_flat,
    ret_np_from_gt_flat,
    rtol=None,
    atol=1e-6,
    specific_tolerance_dict=None,
    backend: str,
    ground_truth_backend="TensorFlow",
    test_dtypes=True,
):
    """Perform a value test for matching the arrays in ret_np_flat and
    ret_from_np_gt_flat.

    Parameters
    ----------
    ret_np_flat
        A list (flattened) containing Numpy arrays. Return from the
        framework to test.
    ret_np_from_gt_flat
        A list (flattened) containing Numpy arrays. Return from the ground
        truth framework.
    rtol
        Relative Tolerance Value.
    atol
        Absolute Tolerance Value.
    specific_tolerance_dict
        (Optional) Dictionary of specific rtol and atol values according to the dtype.
    ground_truth_backend
        Ground Truth Backend Framework.
    test_dtypes
        whether to check the dtypes of the return values match.

    Returns
    -------
    None if the value test passes, else marks the test as failed.
    """
    if test_dtypes: assert_same_type_and_shape([ret_np_flat, ret_np_from_gt_flat])

    if type(ret_np_flat) != list:  # noqa: E721
        ret_np_flat = [ret_np_flat]
    if type(ret_np_from_gt_flat) != list:  # noqa: E721
        ret_np_from_gt_flat = [ret_np_from_gt_flat]
    assert len(ret_np_flat) == len(ret_np_from_gt_flat), (
        f"The length of results from backend {backend} and ground truth framework"
        f" {ground_truth_backend} does not match\n\nlen(ret_np_flat) !="
        f" len(ret_np_from_gt_flat):\n\nret_np_flat:\n\n{ret_np_flat}\n\n"
        f"ret_np_from_gt_flat:\n\n{ret_np_from_gt_flat}"
    )
    # value tests, iterating through each array in the flattened returns
    if specific_tolerance_dict is not None:
        for ret_np, ret_np_from_gt in zip(ret_np_flat, ret_np_from_gt_flat):
            dtype = str(ret_np_from_gt.dtype)
            if specific_tolerance_dict.get(dtype) is not None:
                rtol = specific_tolerance_dict.get(dtype)
            else:
                rtol = TOLERANCE_DICT.get(dtype, 1e-03) if rtol is None else rtol
            assert_all_close(
                ret_np,
                ret_np_from_gt,
                backend=backend,
                rtol=rtol,
                atol=atol,
                ground_truth_backend=ground_truth_backend,
                test_dtypes=test_dtypes,
            )
    elif rtol is not None:
        for ret_np, ret_np_from_gt in zip(ret_np_flat, ret_np_from_gt_flat):
            assert_all_close(
                ret_np,
                ret_np_from_gt,
                backend=backend,
                rtol=rtol,
                atol=atol,
                ground_truth_backend=ground_truth_backend,
                test_dtypes=test_dtypes,
            )
    else:
        for ret_np, ret_np_from_gt in zip(ret_np_flat, ret_np_from_gt_flat):
            rtol = TOLERANCE_DICT.get(str(ret_np_from_gt.dtype), 1e-03)
            assert_all_close(
                ret_np,
                ret_np_from_gt,
                backend=backend,
                rtol=rtol,
                atol=atol,
                ground_truth_backend=ground_truth_backend,
                test_dtypes=test_dtypes,
            )
