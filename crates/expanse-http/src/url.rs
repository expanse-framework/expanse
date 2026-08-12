//! URL type — parses once, exposes read-only components.
//!
//! Python's `urllib.parse.urlsplit` accepts scheme-less inputs like
//! `"/foo?bar#baz"` and returns an empty scheme; the WHATWG `url` crate
//! rejects those. We try the strict parse first and fall back to a manual
//! split for relative inputs, so the type behaves like a lax URL container.

use pyo3::exceptions::PyTypeError;
use pyo3::prelude::*;
use pyo3::types::PyAny;
use url::Url as StdUrl;

#[derive(Clone, Default)]
struct Parsed {
    scheme: String,
    netloc: String,
    path: String,
    query: String,
    fragment: String,
    username: Option<String>,
    password: Option<String>,
    hostname: Option<String>,
    port: Option<u16>,
}

fn build_netloc(u: &StdUrl) -> String {
    let host = u.host_str().unwrap_or("");
    let user = u.username();
    let pw = u.password();
    let port = u.port();

    let mut out = String::new();
    if !user.is_empty() || pw.is_some() {
        out.push_str(user);
        if let Some(pw) = pw {
            out.push(':');
            out.push_str(pw);
        }
        out.push('@');
    }
    out.push_str(host);
    if let Some(port) = port {
        out.push(':');
        out.push_str(&port.to_string());
    }
    out
}

fn manual_split(input: &str) -> Parsed {
    let (before_frag, fragment) = match input.find('#') {
        Some(i) => (&input[..i], input[i + 1..].to_string()),
        None => (input, String::new()),
    };
    let (path, query) = match before_frag.find('?') {
        Some(i) => (
            before_frag[..i].to_string(),
            before_frag[i + 1..].to_string(),
        ),
        None => (before_frag.to_string(), String::new()),
    };
    Parsed {
        path,
        query,
        fragment,
        ..Default::default()
    }
}

fn parse(input: &str) -> Parsed {
    if input.is_empty() {
        return Parsed::default();
    }
    match StdUrl::parse(input) {
        Ok(u) => Parsed {
            scheme: u.scheme().to_string(),
            netloc: build_netloc(&u),
            path: u.path().to_string(),
            query: u.query().unwrap_or("").to_string(),
            fragment: u.fragment().unwrap_or("").to_string(),
            username: if u.username().is_empty() {
                None
            } else {
                Some(u.username().to_string())
            },
            password: u.password().map(String::from),
            hostname: u.host_str().map(String::from),
            port: u.port(),
        },
        Err(_) => manual_split(input),
    }
}

/// Immutable URL container.
///
/// Constructed from a URL string. The Python-side facade in
/// `expanse.http.url` subclasses this to add `from_scope`, `from_components`,
/// `replace`, and to wrap `.path` in `URLPath`. The Rust struct name mirrors
/// the Python one so the two APIs read the same across languages; the
/// `clippy::upper_case_acronyms` lint is silenced accordingly.
#[allow(clippy::upper_case_acronyms)]
#[pyclass(subclass, name = "URL", module = "expanse._expanse_http")]
pub struct URL {
    raw: String,
    parsed: Parsed,
}

#[pymethods]
impl URL {
    #[new]
    #[pyo3(signature = (url = ""))]
    fn new(url: &str) -> Self {
        URL {
            raw: url.to_string(),
            parsed: parse(url),
        }
    }

    #[getter]
    fn full(&self) -> &str {
        &self.raw
    }

    #[getter]
    fn scheme(&self) -> &str {
        &self.parsed.scheme
    }

    #[getter]
    fn netloc(&self) -> &str {
        &self.parsed.netloc
    }

    /// Raw path string. The Python facade wraps this in `URLPath`.
    #[getter(path)]
    fn get_path(&self) -> &str {
        &self.parsed.path
    }

    #[getter]
    fn query(&self) -> &str {
        &self.parsed.query
    }

    #[getter]
    fn fragment(&self) -> &str {
        &self.parsed.fragment
    }

    #[getter]
    fn username(&self) -> Option<&str> {
        self.parsed.username.as_deref()
    }

    #[getter]
    fn password(&self) -> Option<&str> {
        self.parsed.password.as_deref()
    }

    #[getter]
    fn hostname(&self) -> Option<&str> {
        self.parsed.hostname.as_deref()
    }

    #[getter]
    fn port(&self) -> Option<u16> {
        self.parsed.port
    }

    fn is_secure(&self) -> bool {
        self.parsed.scheme == "https"
    }

    fn __str__(&self) -> &str {
        &self.raw
    }

    fn __eq__(&self, other: &Bound<'_, PyAny>) -> PyResult<bool> {
        match other.str() {
            Ok(s) => match s.extract::<String>() {
                Ok(rhs) => Ok(self.raw == rhs),
                Err(_) => Err(PyTypeError::new_err("cannot convert operand to str")),
            },
            Err(_) => Ok(false),
        }
    }

    fn __repr__(&self) -> String {
        let display = if let Some(pw) = &self.parsed.password {
            let needle = format!(":{pw}@");
            self.raw.replacen(&needle, ":********@", 1)
        } else {
            self.raw.clone()
        };
        format!("URL({display:?})")
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<URL>()?;
    Ok(())
}
