//! Rust-accelerated HTTP primitives for the Expanse framework.
//!
//! The pure-Python implementations under `expanse.http._python.*` remain the
//! fallback when this extension is unavailable or `EXPANSE_NO_RUST=1` is set.
//! Rust is the source of truth for behavior when the two diverge.

// `#[pymethods]` uses the `?` operator on `PyResult` internally which trips
// clippy's `useless_conversion` lint (PyErr → PyErr via From). Silenced at
// the crate root so we don't have to sprinkle allows on every method.
#![allow(clippy::useless_conversion)]

use pyo3::prelude::*;

pub const VERSION: &str = env!("CARGO_PKG_VERSION");

mod cookie;
mod headers;
mod url;

#[pyfunction]
fn _hello() -> &'static str {
    "expanse-http (Rust) is live"
}

#[pymodule]
fn _expanse_http(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", VERSION)?;
    m.add_function(wrap_pyfunction!(_hello, m)?)?;
    url::register(m)?;
    headers::register(m)?;
    cookie::register(m)?;
    Ok(())
}
