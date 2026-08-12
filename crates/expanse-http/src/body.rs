//! Body decoders — JSON and application/x-www-form-urlencoded.
//!
//! Multipart is deliberately out of scope for the first pass: parsing it
//! well needs the request body as a stream (Python's ASGI ``receive``
//! callback), which requires bridging Python's asyncio with tokio via
//! ``pyo3-async-runtimes``. That's a separate landing.

use pyo3::exceptions::{PyUnicodeDecodeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyList, PyTuple};

/// Decode a JSON body (given as bytes) into a Python object.
///
/// The Python API here mirrors ``msgspec.json.decode`` — a single call
/// returning a native Python value; on parse failure a ValueError is
/// raised so the caller (Request.json in Python) can wrap it in
/// ``MalformedJSONError``.
#[pyfunction]
#[pyo3(signature = (data, charset = "utf-8"))]
fn decode_json<'py>(
    py: Python<'py>,
    data: &Bound<'_, PyBytes>,
    charset: &str,
) -> PyResult<Bound<'py, PyAny>> {
    let bytes = data.as_bytes();
    let text = if charset.eq_ignore_ascii_case("utf-8") || charset.eq_ignore_ascii_case("utf8") {
        std::str::from_utf8(bytes).map_err(|e| PyUnicodeDecodeError::new_err(e.to_string()))?
    } else {
        // Uncommon charset: hand off to Python's codec system rather than
        // pulling encoding_rs into the wheel.
        let decoded = data.call_method1("decode", (charset,))?;
        return decode_json_str(py, decoded.extract::<String>()?);
    };
    decode_json_str(py, text.to_owned())
}

fn decode_json_str<'py>(py: Python<'py>, text: String) -> PyResult<Bound<'py, PyAny>> {
    let value: serde_json::Value =
        serde_json::from_str(&text).map_err(|e| PyValueError::new_err(e.to_string()))?;
    Ok(pythonize::pythonize(py, &value)?)
}

/// Decode an ``application/x-www-form-urlencoded`` body.
///
/// Returns a list of ``(name, value)`` tuples, matching ``parse_qsl``'s
/// output shape so callers can hand it straight to ``FormData``.
#[pyfunction]
#[pyo3(signature = (data, charset = "latin-1"))]
fn decode_urlencoded<'py>(
    py: Python<'py>,
    data: &Bound<'_, PyBytes>,
    charset: &str,
) -> PyResult<Bound<'py, PyList>> {
    let text = if charset.eq_ignore_ascii_case("utf-8")
        || charset.eq_ignore_ascii_case("utf8")
        || charset.eq_ignore_ascii_case("latin-1")
        || charset.eq_ignore_ascii_case("latin1")
    {
        // latin-1 is a lossless one-to-one byte→char mapping; utf-8 needs
        // validation but the common case is valid.
        if charset.starts_with("utf") {
            std::str::from_utf8(data.as_bytes())
                .map_err(|e| PyUnicodeDecodeError::new_err(e.to_string()))?
                .to_owned()
        } else {
            data.as_bytes().iter().map(|&b| b as char).collect()
        }
    } else {
        let decoded = data.call_method1("decode", (charset,))?;
        decoded.extract::<String>()?
    };

    let pairs = url::form_urlencoded::parse(text.as_bytes());
    let list = PyList::empty_bound(py);
    for (k, v) in pairs {
        let tuple = PyTuple::new_bound(py, [k.as_ref(), v.as_ref()]);
        list.append(tuple)?;
    }
    Ok(list)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(decode_json, m)?)?;
    m.add_function(wrap_pyfunction!(decode_urlencoded, m)?)?;
    Ok(())
}
