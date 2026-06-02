pub struct HttpRequest<'a> {
    pub method: &'a str,
    pub uri: &'a str,
    pub headers: Vec<(&'a str, &'a str)>,
}

impl<'a> HttpRequest<'a> {
    pub fn parse(buffer: &'a [u8]) -> Result<Self, &'static str> {
        let mut lines = buffer.split(|&b| b == 10);
        
        let first_line = lines.next().ok_or("Empty request")?;
        let first_line = if first_line.ends_with(b"\r") {
            &first_line[..first_line.len() - 1]
        } else {
            first_line
        };

        let mut parts = first_line.split(|&b| b == 32);
        let method_bytes = parts.next().ok_or("Missing method")?;
        let uri_bytes = parts.next().ok_or("Missing URI")?;
        let version_bytes = parts.next().ok_or("Missing version")?;

        if parts.next().is_some() {
            return Err("Malformed request line");
        }

        let version_str = std::str::from_utf8(version_bytes).map_err(|_| "Invalid UTF-8 in version")?;
        if version_str != "HTTP\x2f1.1" && version_str != "HTTP\x2f1.0" {
            return Err("Unsupported HTTP version");
        }

        let method = std::str::from_utf8(method_bytes).map_err(|_| "Invalid UTF-8 in method")?;
        let uri = std::str::from_utf8(uri_bytes).map_err(|_| "Invalid UTF-8 in URI")?;

        let mut headers = Vec::new();
        for line in lines {
            let line = if line.ends_with(b"\r") {
                &line[..line.len() - 1]
            } else {
                line
            };

            if line.is_empty() {
                break;
            }

            let mut header_parts = line.splitn(2, |&b| b == 58);
            let name_bytes = header_parts.next().ok_or("Malformed header name")?;
            let value_bytes = header_parts.next().ok_or("Malformed header value")?;

            let name = std::str::from_utf8(name_bytes).map_err(|_| "Invalid UTF-8 in header name")?.trim();
            let value = std::str::from_utf8(value_bytes).map_err(|_| "Invalid UTF-8 in header value")?.trim();

            headers.push((name, value));
        }

        Ok(HttpRequest {
            method,
            uri,
            headers,
        })
    }
}
