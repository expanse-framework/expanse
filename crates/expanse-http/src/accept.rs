//! AcceptHeader / AcceptHeaderItem — RFC 7231 accept-header parsing and
//! quality-based sorting.

use indexmap::IndexMap;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

fn parse_item(raw: &str) -> (String, f64, IndexMap<String, String>) {
    let mut parts = raw.splitn(2, ';');
    let value = parts.next().unwrap_or("").trim().to_owned();
    let attrs_str = parts.next().unwrap_or("");
    let mut attrs = IndexMap::new();
    let mut quality = 1.0_f64;
    for chunk in attrs_str.split(';') {
        let chunk = chunk.trim();
        if let Some((k, v)) = chunk.split_once('=') {
            let k = k.trim();
            let v = v.trim();
            if k.eq_ignore_ascii_case("q") {
                if let Ok(q) = v.parse::<f64>() {
                    quality = q;
                }
            } else if !k.is_empty() {
                attrs.insert(k.to_owned(), v.to_owned());
            }
        }
    }
    (value, quality, attrs)
}

#[pyclass(name = "AcceptHeaderItem", module = "expanse._expanse_http")]
#[derive(Clone)]
pub struct AcceptHeaderItem {
    value: String,
    quality: f64,
    index: i64,
    attributes: IndexMap<String, String>,
}

#[pymethods]
impl AcceptHeaderItem {
    #[new]
    #[pyo3(signature = (value, attributes = None))]
    fn new(value: String, attributes: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let mut item = AcceptHeaderItem {
            value,
            quality: 1.0,
            index: 0,
            attributes: IndexMap::new(),
        };
        if let Some(attrs) = attributes {
            if !attrs.is_none() {
                let dict = attrs
                    .downcast::<pyo3::types::PyDict>()
                    .map_err(|_| PyValueError::new_err("attributes must be a dict"))?;
                for (k, v) in dict.iter() {
                    item.set_attribute(k.extract()?, v.extract()?);
                }
            }
        }
        Ok(item)
    }

    #[classmethod]
    fn from_string(_cls: &Bound<'_, pyo3::types::PyType>, item: &str) -> Self {
        let (value, quality, attrs) = parse_item(item);
        AcceptHeaderItem {
            value,
            quality,
            index: 0,
            attributes: attrs,
        }
    }

    #[getter]
    fn value(&self) -> &str {
        &self.value
    }

    #[getter]
    fn quality(&self) -> f64 {
        self.quality
    }

    #[getter]
    fn index(&self) -> i64 {
        self.index
    }

    fn set_index(mut slf: PyRefMut<'_, Self>, index: i64) -> PyRefMut<'_, Self> {
        slf.index = index;
        slf
    }

    fn set_attribute(&mut self, name: String, value: String) {
        if name == "q" {
            if let Ok(q) = value.parse::<f64>() {
                self.quality = q;
            }
        } else {
            self.attributes.insert(name, value);
        }
    }

    fn __str__(&self) -> String {
        let mut out = self.value.clone();
        if self.quality < 1.0 {
            out.push_str(&format!(";q={}", self.quality));
        }
        if !self.attributes.is_empty() {
            let pairs: Vec<String> = self
                .attributes
                .iter()
                .map(|(k, v)| format!("{k} {v}"))
                .collect();
            out.push_str(&format!("; {}", pairs.join(";")));
        }
        out
    }
}

#[pyclass(name = "AcceptHeader", module = "expanse._expanse_http")]
pub struct AcceptHeader {
    items: Vec<AcceptHeaderItem>,
    sorted: bool,
}

#[pymethods]
impl AcceptHeader {
    #[new]
    #[pyo3(signature = (items = None))]
    fn new(items: Option<Vec<AcceptHeaderItem>>) -> Self {
        AcceptHeader {
            items: items.unwrap_or_default(),
            sorted: false,
        }
    }

    #[classmethod]
    fn from_string(_cls: &Bound<'_, pyo3::types::PyType>, header: &str) -> Self {
        let items: Vec<AcceptHeaderItem> = header
            .split(',')
            .enumerate()
            .map(|(i, raw)| {
                let (value, quality, attrs) = parse_item(raw.trim());
                AcceptHeaderItem {
                    value,
                    quality,
                    index: i as i64,
                    attributes: attrs,
                }
            })
            .collect();
        AcceptHeader {
            items,
            sorted: false,
        }
    }

    fn all(&mut self) -> Vec<AcceptHeaderItem> {
        if !self.sorted {
            self.items.sort_by(|a, b| {
                b.quality
                    .partial_cmp(&a.quality)
                    .unwrap_or(std::cmp::Ordering::Equal)
                    .then(a.index.cmp(&b.index))
            });
            self.sorted = true;
        }
        self.items.clone()
    }

    fn __str__(&self) -> String {
        self.items
            .iter()
            .map(|i| i.__str__())
            .collect::<Vec<_>>()
            .join(", ")
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<AcceptHeaderItem>()?;
    m.add_class::<AcceptHeader>()?;
    Ok(())
}
