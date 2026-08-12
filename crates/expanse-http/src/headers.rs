//! HeaderBag and ResponseHeaderBag.
//!
//! Case-insensitive, order-preserving multi-value header stores that mirror
//! the semantics of `expanse.http._python.header_bag.HeaderBag`. Both are
//! exposed as PyO3 classes and implement the mapping protocol; the Python
//! facade mixes in `collections.abc.MutableMapping` so callers get
//! `update`, `setdefault`, `__contains__`, etc. for free.

use indexmap::IndexMap;
use pyo3::exceptions::{PyKeyError, PyTypeError};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList, PyString, PyTuple};

/// The Python API accepts `str | list[str | None] | None` for values.
/// We collapse that into a `Vec<String>` (dropping Nones — the Python impl
/// filters them out on join anyway), so downstream consumers never need to
/// worry about mixed-nullability lists.
fn coerce_value(value: &Bound<'_, PyAny>) -> PyResult<Vec<String>> {
    if value.is_none() {
        return Ok(Vec::new());
    }
    if let Ok(s) = value.downcast::<PyString>() {
        return Ok(vec![s.to_str()?.to_owned()]);
    }
    if let Ok(list) = value.downcast::<PyList>() {
        let mut out = Vec::with_capacity(list.len());
        for item in list.iter() {
            if item.is_none() {
                continue;
            }
            let s: String = item.extract()?;
            out.push(s);
        }
        return Ok(out);
    }
    Err(PyTypeError::new_err(
        "header value must be str, list[str | None], or None",
    ))
}

fn normalize(name: &str) -> String {
    name.to_ascii_lowercase()
}

#[allow(clippy::to_string_in_format_args)]
fn join_values(values: &[String]) -> String {
    values.join(",")
}

/// Case-insensitive, order-preserving multi-value header store.
#[pyclass(
    subclass,
    name = "HeaderBag",
    module = "expanse._expanse_http",
    mapping
)]
pub struct HeaderBag {
    headers: IndexMap<String, Vec<String>>,
}

impl HeaderBag {
    fn insert(&mut self, name: &str, values: Vec<String>, replace: bool) {
        let key = normalize(name);
        if replace {
            self.headers.insert(key, values);
        } else {
            self.headers.entry(key).or_default().extend(values);
        }
    }
}

#[pymethods]
impl HeaderBag {
    #[new]
    #[pyo3(signature = (headers = None))]
    fn new(headers: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let mut bag = HeaderBag {
            headers: IndexMap::new(),
        };
        if let Some(h) = headers {
            if !h.is_none() {
                let dict = h.downcast::<PyDict>().map_err(|_| {
                    PyTypeError::new_err("headers must be a Mapping[str, str] or None")
                })?;
                for (k, v) in dict.iter() {
                    let key: String = k.extract()?;
                    let values = coerce_value(&v)?;
                    bag.insert(&key, values, true);
                }
            }
        }
        Ok(bag)
    }

    /// If a key is given, return the list of values for that header (empty
    /// list when absent). Without arguments, return the underlying dict of
    /// lowercased-key → values.
    #[pyo3(signature = (key = None))]
    fn all<'py>(&self, py: Python<'py>, key: Option<&str>) -> PyResult<Bound<'py, PyAny>> {
        match key {
            Some(k) => {
                let values: Vec<String> =
                    self.headers.get(&normalize(k)).cloned().unwrap_or_default();
                Ok(PyList::new_bound(py, values).into_any())
            }
            None => {
                let dict = PyDict::new_bound(py);
                for (k, v) in &self.headers {
                    dict.set_item(k, PyList::new_bound(py, v))?;
                }
                Ok(dict.into_any())
            }
        }
    }

    #[pyo3(signature = (key, default = None))]
    fn get<'py>(
        &self,
        py: Python<'py>,
        key: &str,
        default: Option<Bound<'py, PyAny>>,
    ) -> PyResult<Bound<'py, PyAny>> {
        match self.headers.get(&normalize(key)) {
            Some(values) if !values.is_empty() => {
                Ok(PyString::new_bound(py, &values[0]).into_any())
            }
            _ => Ok(default.unwrap_or_else(|| py.None().into_bound(py))),
        }
    }

    #[pyo3(signature = (name, value, replace = true))]
    fn set(&mut self, name: &str, value: &Bound<'_, PyAny>, replace: bool) -> PyResult<()> {
        let values = coerce_value(value)?;
        self.insert(name, values, replace);
        Ok(())
    }

    fn has(&self, name: &str) -> bool {
        self.headers.contains_key(&normalize(name))
    }

    fn remove(&mut self, name: &str) {
        self.headers.shift_remove(&normalize(name));
    }

    /// ASGI-ready: `[(b"header-name", b"comma,joined,values"), …]`.
    fn encode<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
        let list = PyList::empty_bound(py);
        for (k, v) in &self.headers {
            let key_bytes = pyo3::types::PyBytes::new_bound(py, k.as_bytes());
            let val_bytes = pyo3::types::PyBytes::new_bound(py, join_values(v).as_bytes());
            list.append(PyTuple::new_bound(
                py,
                [key_bytes.into_any(), val_bytes.into_any()],
            ))?;
        }
        Ok(list)
    }

    fn __getitem__<'py>(&self, py: Python<'py>, name: &str) -> PyResult<Bound<'py, PyString>> {
        match self.headers.get(&normalize(name)) {
            Some(values) if !values.is_empty() => Ok(PyString::new_bound(py, &values[0])),
            _ => Err(PyKeyError::new_err(format!(
                "Header '{}' not found.",
                normalize(name)
            ))),
        }
    }

    fn __setitem__(&mut self, name: &str, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.set(name, value, true)
    }

    fn __delitem__(&mut self, name: &str) -> PyResult<()> {
        if !self.headers.contains_key(&normalize(name)) {
            return Err(PyKeyError::new_err(format!(
                "Header '{}' not found.",
                normalize(name)
            )));
        }
        self.remove(name);
        Ok(())
    }

    fn __contains__(&self, name: &str) -> bool {
        self.has(name)
    }

    fn __len__(&self) -> usize {
        self.headers.len()
    }

    fn __iter__<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let keys: Vec<String> = self.headers.keys().cloned().collect();
        PyList::new_bound(py, keys)
            .into_any()
            .call_method0("__iter__")
    }

    fn __repr__(&self) -> String {
        // Match Python's dict repr — single-quoted keys/values, since tests
        // compare against strings produced by CPython's dict.__repr__.
        let mut s = String::from("HeaderBag({");
        for (i, (k, v)) in self.headers.iter().enumerate() {
            if i > 0 {
                s.push_str(", ");
            }
            s.push('\'');
            s.push_str(k);
            s.push_str("': [");
            for (j, item) in v.iter().enumerate() {
                if j > 0 {
                    s.push_str(", ");
                }
                s.push('\'');
                s.push_str(item);
                s.push('\'');
            }
            s.push(']');
        }
        s.push_str("})");
        s
    }

    fn __str__(&self) -> String {
        if self.headers.is_empty() {
            return String::new();
        }
        let mut pairs: Vec<(&String, &Vec<String>)> = self.headers.iter().collect();
        pairs.sort_by(|a, b| a.0.cmp(b.0));
        let mut out = String::new();
        for (k, v) in pairs {
            out.push_str(&title_case(k));
            out.push_str(": ");
            out.push_str(&join_values_pretty(v));
            out.push_str("\r\n");
        }
        out
    }
}

fn title_case(name: &str) -> String {
    name.split('-')
        .map(|part| {
            let mut chars = part.chars();
            match chars.next() {
                Some(c) => c.to_ascii_uppercase().to_string() + chars.as_str(),
                None => String::new(),
            }
        })
        .collect::<Vec<_>>()
        .join("-")
}

fn join_values_pretty(values: &[String]) -> String {
    values.join(", ")
}

/// Same store, plus preservation of the original casing used when a header
/// was first set — matters for wire-format response headers.
#[pyclass(subclass, extends = HeaderBag, name = "ResponseHeaderBag", module = "expanse._expanse_http")]
pub struct ResponseHeaderBag {
    header_names: IndexMap<String, String>,
}

#[pymethods]
impl ResponseHeaderBag {
    #[new]
    #[pyo3(signature = (headers = None))]
    fn new(headers: Option<&Bound<'_, PyAny>>) -> PyResult<(Self, HeaderBag)> {
        let mut names = IndexMap::new();
        // Base HeaderBag construction populates the values.
        let bag = HeaderBag::new(headers.as_ref().copied())?;
        // Now record the original casing for each header we accepted.
        if let Some(h) = headers {
            if !h.is_none() {
                let dict = h.downcast::<PyDict>().map_err(|_| {
                    PyTypeError::new_err("headers must be a Mapping[str, str] or None")
                })?;
                for (k, _) in dict.iter() {
                    let original: String = k.extract()?;
                    names.insert(normalize(&original), original);
                }
            }
        }
        Ok((
            ResponseHeaderBag {
                header_names: names,
            },
            bag,
        ))
    }

    #[pyo3(signature = (name, value, replace = true))]
    fn set(
        mut slf: PyRefMut<'_, Self>,
        name: &str,
        value: &Bound<'_, PyAny>,
        replace: bool,
    ) -> PyResult<()> {
        slf.header_names.insert(normalize(name), name.to_owned());
        let mut parent = slf.into_super();
        parent.set(name, value, replace)
    }

    fn remove(mut slf: PyRefMut<'_, Self>, name: &str) {
        slf.header_names.shift_remove(&normalize(name));
        let mut parent = slf.into_super();
        parent.remove(name);
    }

    fn __setitem__(slf: PyRefMut<'_, Self>, name: &str, value: &Bound<'_, PyAny>) -> PyResult<()> {
        Self::set(slf, name, value, true)
    }

    fn __delitem__(slf: PyRefMut<'_, Self>, name: &str) -> PyResult<()> {
        let normalized = normalize(name);
        if !slf.as_ref().has(name) {
            return Err(PyKeyError::new_err(format!(
                "Header '{normalized}' not found."
            )));
        }
        Self::remove(slf, name);
        Ok(())
    }

    /// Preserves the original header casing for wire format.
    fn encode<'py>(slf: PyRef<'_, Self>, py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
        let list = PyList::empty_bound(py);
        let parent = slf.as_ref();
        for (normalized, values) in parent.headers.iter() {
            let original = slf
                .header_names
                .get(normalized)
                .cloned()
                .unwrap_or_else(|| normalized.clone());
            let key_bytes = pyo3::types::PyBytes::new_bound(py, original.as_bytes());
            let val_bytes = pyo3::types::PyBytes::new_bound(py, join_values(values).as_bytes());
            list.append(PyTuple::new_bound(
                py,
                [key_bytes.into_any(), val_bytes.into_any()],
            ))?;
        }
        Ok(list)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<HeaderBag>()?;
    m.add_class::<ResponseHeaderBag>()?;
    Ok(())
}
