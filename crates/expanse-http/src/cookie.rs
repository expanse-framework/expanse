//! Cookie value type — mirrors the Python implementation's behavior.
//!
//! The `cookie` crate handles the standard RFC 6265 formatting, but the
//! existing Expanse impl has a couple of quirks worth preserving: empty
//! values serialize as ``deleted; expires=Thu, 01 Jan 1970 …; Max-Age=0``
//! (the "delete-me" cookie sentinel), and quoting is done via a custom
//! translation table rather than percent-encoding. We port the logic
//! directly so behavior matches; the `cookie` crate is kept as a Cargo dep
//! for future parsing paths that don't need this exact serialization.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyString};

const LEGAL_KEY_CHARS: &str =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!#$%&'*+-.^_`|~:";
// Characters that CPython's http.cookies also passes through unquoted;
// matches the Python impl's translator exclusion list.
const EXTRA_PASSTHROUGH: &str = " ()/<=>?@[]{}";

fn is_legal_key(value: &str) -> bool {
    !value.is_empty()
        && value
            .bytes()
            .all(|b| LEGAL_KEY_CHARS.as_bytes().contains(&b))
}

fn quote(value: &str) -> String {
    if is_legal_key(value) {
        return value.to_owned();
    }
    let mut out = String::with_capacity(value.len() + 2);
    out.push('"');
    for c in value.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            _ if (c as u32) < 256
                && !LEGAL_KEY_CHARS.contains(c)
                && !EXTRA_PASSTHROUGH.contains(c) =>
            {
                out.push_str(&format!("\\{:03o}", c as u32));
            }
            _ => out.push(c),
        }
    }
    out.push('"');
    out
}

const MONTHS: [&str; 12] = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];
const WEEKDAYS: [&str; 7] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/// Format a Unix timestamp as ``Wkday, DD Mon YYYY HH:MM:SS GMT``.
fn format_expires(ts: i64) -> String {
    // Days since 1970-01-01 Thursday (weekday index 3).
    let days = ts.div_euclid(86_400);
    let secs = ts.rem_euclid(86_400);
    let weekday = (((days % 7) + 3 + 7) % 7) as usize;

    // Gregorian date from days-since-epoch. Standard leap-year math.
    let mut year = 1970_i64;
    let mut d = days;
    loop {
        let ydays = if is_leap(year) { 366 } else { 365 };
        if d < ydays {
            break;
        }
        d -= ydays;
        year += 1;
    }
    while d < 0 {
        year -= 1;
        d += if is_leap(year) { 366 } else { 365 };
    }
    let mdays: [i64; 12] = [
        31,
        if is_leap(year) { 29 } else { 28 },
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ];
    let mut month = 0;
    let mut day = d;
    while day >= mdays[month] {
        day -= mdays[month];
        month += 1;
    }
    let hour = secs / 3600;
    let minute = (secs % 3600) / 60;
    let second = secs % 60;
    format!(
        "{}, {:02} {} {:04} {:02}:{:02}:{:02} GMT",
        WEEKDAYS[weekday],
        day + 1,
        MONTHS[month],
        year,
        hour,
        minute,
        second,
    )
}

fn is_leap(year: i64) -> bool {
    (year % 4 == 0 && year % 100 != 0) || year % 400 == 0
}

fn now_secs() -> i64 {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0)
}

fn compute_expires(value: &Bound<'_, PyAny>) -> PyResult<i64> {
    if value.is_none() {
        return Ok(0);
    }
    // Numeric first (int/float timestamps — the common case).
    if let Ok(n) = value.extract::<f64>() {
        return Ok((n as i64).max(0));
    }
    // Datetime-like: any object with a callable ``.timestamp()``. Avoids
    // pulling in pyo3's chrono feature just to detect datetimes.
    if let Ok(ts_method) = value.getattr("timestamp") {
        let ts: f64 = ts_method.call0()?.extract()?;
        return Ok((ts as i64).max(0));
    }
    Err(pyo3::exceptions::PyTypeError::new_err(
        "expires must be int, float, or datetime",
    ))
}

/// SameSite attribute values. Case-preserved to match CPython's StrEnum
/// serialization (`"lax"`, `"strict"`, `"none"`).
#[pyclass(name = "SameSite", module = "expanse._expanse_http", eq, eq_int)]
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum SameSite {
    Lax,
    Strict,
    None_,
}

#[pymethods]
impl SameSite {
    #[classattr]
    #[allow(non_snake_case)]
    fn LAX() -> Self {
        SameSite::Lax
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn STRICT() -> Self {
        SameSite::Strict
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn NONE() -> Self {
        SameSite::None_
    }

    #[getter]
    fn value(&self) -> &'static str {
        match self {
            SameSite::Lax => "lax",
            SameSite::Strict => "strict",
            SameSite::None_ => "none",
        }
    }

    fn __str__(&self) -> &'static str {
        self.value()
    }

    fn __repr__(&self) -> String {
        format!("<SameSite.{}: {:?}>", self.name(), self.value())
    }
}

impl SameSite {
    fn name(&self) -> &'static str {
        match self {
            SameSite::Lax => "LAX",
            SameSite::Strict => "STRICT",
            SameSite::None_ => "NONE",
        }
    }
}

fn same_site_from_any(value: &Bound<'_, PyAny>) -> PyResult<Option<SameSite>> {
    if value.is_none() {
        return Ok(None);
    }
    if let Ok(v) = value.extract::<PyRef<'_, SameSite>>() {
        return Ok(Some(*v));
    }
    if let Ok(s) = value.downcast::<PyString>() {
        return match s.to_str()?.to_ascii_lowercase().as_str() {
            "lax" => Ok(Some(SameSite::Lax)),
            "strict" => Ok(Some(SameSite::Strict)),
            "none" => Ok(Some(SameSite::None_)),
            other => Err(PyValueError::new_err(format!(
                "invalid SameSite value: '{other}'"
            ))),
        };
    }
    Err(PyValueError::new_err(
        "same_site must be a SameSite, str or None",
    ))
}

/// Cookie value object. Immutable except for the internal ``secure_default``
/// flag flipped by :meth:`set_secure_default` during response preparation.
#[pyclass(subclass, name = "Cookie", module = "expanse._expanse_http")]
#[derive(Clone)]
pub struct Cookie {
    name: String,
    value: Option<String>,
    expires: i64,
    domain: Option<String>,
    path: String,
    secure: Option<bool>,
    http_only: bool,
    same_site: Option<SameSite>,
    partitioned: bool,
    secure_default: bool,
}

impl Cookie {
    fn max_age(&self) -> i64 {
        let max = self.expires - now_secs();
        max.max(0)
    }

    fn serialize(&self) -> String {
        let mut out = String::new();
        out.push_str(&quote(&self.name));
        out.push('=');

        match &self.value {
            None => {
                out.push_str("deleted; expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age=0");
            }
            Some(v) if v.is_empty() => {
                out.push_str("deleted; expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age=0");
            }
            Some(v) => {
                out.push_str(&quote(v));
                if self.expires != 0 {
                    out.push_str("; expires=");
                    out.push_str(&format_expires(self.expires));
                    out.push_str("; Max-Age=");
                    out.push_str(&self.max_age().to_string());
                }
            }
        }

        if let Some(d) = &self.domain {
            out.push_str("; domain=");
            out.push_str(d);
        }
        if !self.path.is_empty() {
            out.push_str("; path=");
            out.push_str(&self.path);
        }
        if self.is_secure() {
            out.push_str("; secure");
        }
        if self.http_only {
            out.push_str("; httponly");
        }
        if let Some(ss) = self.same_site {
            out.push_str("; samesite=");
            out.push_str(ss.value());
        }
        if self.partitioned {
            out.push_str("; partitioned");
        }
        out
    }
}

#[pymethods]
impl Cookie {
    #[new]
    #[pyo3(signature = (
        name,
        value = None,
        expires = None,
        domain = None,
        path = None,
        secure = None,
        http_only = false,
        same_site = None,
        partitioned = false,
    ))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        name: String,
        value: Option<String>,
        expires: Option<Bound<'_, PyAny>>,
        domain: Option<String>,
        path: Option<String>,
        secure: Option<bool>,
        http_only: bool,
        same_site: Option<Bound<'_, PyAny>>,
        partitioned: bool,
    ) -> PyResult<Self> {
        let expires_ts = match expires {
            Some(v) => compute_expires(&v)?,
            None => 0,
        };
        // Rust `None` here can mean either "argument absent" or "explicit
        // Python None" — PyO3's Option collapses both cases. The Python
        // facade at expanse.http.cookie.Cookie disambiguates and sends the
        // sentinel SameSite.LAX for the default case, so Rust None here
        // unambiguously means "no SameSite attribute on the wire".
        let ss = match same_site {
            Some(v) => same_site_from_any(&v)?,
            None => None,
        };
        Ok(Cookie {
            name,
            value,
            expires: expires_ts,
            domain,
            path: path.unwrap_or_else(|| "/".to_string()),
            secure,
            http_only,
            same_site: ss,
            partitioned,
            secure_default: false,
        })
    }

    #[getter]
    fn name(&self) -> &str {
        &self.name
    }

    #[getter]
    fn value(&self) -> Option<&str> {
        self.value.as_deref()
    }

    #[getter]
    fn expires(&self) -> i64 {
        self.expires
    }

    #[getter]
    fn domain(&self) -> Option<&str> {
        self.domain.as_deref()
    }

    #[getter]
    fn path(&self) -> &str {
        &self.path
    }

    fn is_secure(&self) -> bool {
        self.secure.unwrap_or(self.secure_default)
    }

    fn is_http_only(&self) -> bool {
        self.http_only
    }

    #[getter]
    fn same_site(&self) -> Option<SameSite> {
        self.same_site
    }

    fn is_partitioned(&self) -> bool {
        self.partitioned
    }

    #[getter(max_age)]
    fn py_max_age(&self) -> i64 {
        self.max_age()
    }

    #[pyo3(signature = (value = None))]
    fn with_value(&self, value: Option<String>) -> Self {
        let mut c = self.clone();
        c.value = value;
        c
    }

    fn with_expires(&self, expires: Bound<'_, PyAny>) -> PyResult<Self> {
        let mut c = self.clone();
        c.expires = compute_expires(&expires)?;
        Ok(c)
    }

    #[pyo3(signature = (domain = None))]
    fn with_domain(&self, domain: Option<String>) -> Self {
        let mut c = self.clone();
        c.domain = domain;
        c
    }

    #[pyo3(signature = (path = None))]
    fn with_path(&self, path: Option<String>) -> Self {
        let mut c = self.clone();
        c.path = match path {
            Some(p) if !p.is_empty() => p,
            _ => "/".to_string(),
        };
        c
    }

    #[pyo3(signature = (secure = true))]
    fn with_secure(&self, secure: bool) -> Self {
        let mut c = self.clone();
        c.secure = Some(secure);
        c
    }

    #[pyo3(signature = (http_only = true))]
    fn with_http_only(&self, http_only: bool) -> Self {
        let mut c = self.clone();
        c.http_only = http_only;
        c
    }

    fn with_same_site(&self, same_site: Bound<'_, PyAny>) -> PyResult<Self> {
        let mut c = self.clone();
        c.same_site = same_site_from_any(&same_site)?;
        Ok(c)
    }

    #[pyo3(signature = (partitioned = true))]
    fn with_partitioned(&self, partitioned: bool) -> Self {
        let mut c = self.clone();
        c.partitioned = partitioned;
        c
    }

    fn set_secure_default(mut slf: PyRefMut<'_, Self>, secure: bool) -> PyRefMut<'_, Self> {
        slf.secure_default = secure;
        slf
    }

    fn __str__(&self) -> String {
        self.serialize()
    }

    fn __bytes__<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, pyo3::types::PyBytes>> {
        Ok(pyo3::types::PyBytes::new_bound(
            py,
            self.serialize().as_bytes(),
        ))
    }

    fn __repr__(&self) -> String {
        format!("<Cookie {}>", self.serialize())
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<SameSite>()?;
    m.add_class::<Cookie>()?;
    Ok(())
}
