//! ContentType — light wrapper around a MIME type plus its parameters.
//!
//! We don't use the `mime` crate here because the Python impl compares
//! ``ContentType == "text/plain"`` by looking only at the type portion,
//! and its ``__str__`` puts parameters right after the type without the
//! optional whitespace that `mime` inserts. Direct port keeps parity.

use indexmap::IndexMap;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyString};

#[pyclass(name = "ContentType", module = "expanse._expanse_http")]
#[derive(Clone)]
pub struct ContentType {
    ctype: String,
    options: IndexMap<String, String>,
}

#[pymethods]
impl ContentType {
    #[new]
    fn new(ctype: String, options: &Bound<'_, PyAny>) -> PyResult<Self> {
        let mut opts = IndexMap::new();
        if !options.is_none() {
            let dict = options
                .downcast::<pyo3::types::PyDict>()
                .map_err(|_| pyo3::exceptions::PyTypeError::new_err("options must be a dict"))?;
            for (k, v) in dict.iter() {
                opts.insert(k.extract()?, v.extract()?);
            }
        }
        Ok(ContentType {
            ctype,
            options: opts,
        })
    }

    #[classmethod]
    fn from_string(_cls: &Bound<'_, pyo3::types::PyType>, raw: &str) -> Self {
        let mut parts = raw.split(';');
        let ctype = parts.next().unwrap_or("").trim().to_owned();
        let mut opts = IndexMap::new();
        for part in parts {
            let part = part.trim();
            if let Some((k, v)) = part.split_once('=') {
                opts.insert(k.trim().to_owned(), v.trim().to_owned());
            } else if !part.is_empty() {
                opts.insert(part.to_owned(), String::new());
            }
        }
        ContentType {
            ctype,
            options: opts,
        }
    }

    #[getter(r#type)]
    fn get_type(&self) -> &str {
        &self.ctype
    }

    #[getter]
    fn options<'py>(&self, py: Python<'py>) -> Bound<'py, pyo3::types::PyDict> {
        let dict = pyo3::types::PyDict::new_bound(py);
        for (k, v) in &self.options {
            dict.set_item(k, v).ok();
        }
        dict
    }

    fn __str__(&self) -> String {
        let mut out = self.ctype.clone();
        for (k, v) in &self.options {
            out.push_str(&format!("; {k}={v}"));
        }
        out
    }

    fn __repr__(&self) -> String {
        format!("<ContentType: {}>", self.__str__())
    }

    fn __eq__(&self, other: &Bound<'_, PyAny>) -> PyResult<bool> {
        if let Ok(s) = other.downcast::<PyString>() {
            return Ok(self.ctype == s.to_str()?);
        }
        Ok(false)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<ContentType>()?;
    Ok(())
}
