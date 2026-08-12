//! Response-side helpers.
//!
//! Most of the response wire format is already produced by
//! ``HeaderBag.encode`` and ``Cookie.__bytes__``, both of which are in
//! Rust. This module fuses those two lists in a single call so the hot
//! ``Response.encode_headers`` path doesn't cross the Python↔Rust
//! boundary once per cookie.

use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyList, PyTuple};

/// Combine encoded response headers with the set-cookie lines produced
/// by each cookie's serialization.
///
/// Equivalent to::
///
///     bag.encode() + [(b"set-cookie", bytes(c)) for c in cookies]
///
/// but built up in a single pass so we don't allocate two intermediate
/// Python lists.
#[pyfunction]
fn encode_response_headers<'py>(
    py: Python<'py>,
    headers_encoded: &Bound<'_, PyList>,
    cookies: &Bound<'_, PyList>,
) -> PyResult<Bound<'py, PyList>> {
    let out = PyList::empty_bound(py);
    for item in headers_encoded.iter() {
        out.append(item)?;
    }
    let set_cookie_key = PyBytes::new_bound(py, b"set-cookie");
    for cookie in cookies.iter() {
        let value: Bound<'_, PyBytes> = cookie.call_method0("__bytes__")?.downcast_into()?;
        out.append(PyTuple::new_bound(
            py,
            [set_cookie_key.as_any(), value.as_any()],
        ))?;
    }
    Ok(out)
}

/// Status-code classification. Kept alongside encode so callers can pull
/// everything response-shaped from one Rust module.
#[pyfunction]
fn is_empty_status(status: u16) -> bool {
    matches!(status, 204 | 205 | 304)
}

#[pyfunction]
fn is_informational_status(status: u16) -> bool {
    (100..200).contains(&status)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(encode_response_headers, m)?)?;
    m.add_function(wrap_pyfunction!(is_empty_status, m)?)?;
    m.add_function(wrap_pyfunction!(is_informational_status, m)?)?;
    Ok(())
}
