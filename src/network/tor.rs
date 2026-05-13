use std::io::{Read, Write};
use std::net::TcpStream;
use std::time::Duration;

pub fn renew_tor_identity() -> Result<(), String> {
    let ports = [9051u16, 9151];

    for &port in &ports {
        match try_renew_on_port(port) {
            Ok(()) => return Ok(()),
            Err(e) if e == "ConnectionRefused" => continue,
            Err(e) => return Err(e),
        }
    }

    Err("ConnectionRefused".to_string())
}

fn try_renew_on_port(port: u16) -> Result<(), String> {
    let addr = format!("127.0.0.1:{}", port);
    let mut stream = TcpStream::connect_timeout(
        &addr.parse().map_err(|_| "Invalid address".to_string())?,
        Duration::from_secs(2),
    )
    .map_err(|e| {
        if e.kind() == std::io::ErrorKind::ConnectionRefused {
            "ConnectionRefused".to_string()
        } else {
            format!("Connection error: {}", e)
        }
    })?;

    stream
        .set_read_timeout(Some(Duration::from_secs(2)))
        .map_err(|e| e.to_string())?;

    // Send AUTHENTICATE - try null auth first
    stream
        .write_all(b"AUTHENTICATE \"\"\r\n")
        .map_err(|e| e.to_string())?;

    let mut buf = [0u8; 1024];
    let n = stream.read(&mut buf).map_err(|e| e.to_string())?;
    let resp = String::from_utf8_lossy(&buf[..n]);

    if !resp.starts_with("250") {
        return Err(format!("AuthFailed: {}", resp.trim()));
    }

    // Send NEWNYM signal
    stream
        .write_all(b"SIGNAL NEWNYM\r\n")
        .map_err(|e| e.to_string())?;

    let n = stream.read(&mut buf).map_err(|e| e.to_string())?;
    let resp = String::from_utf8_lossy(&buf[..n]);

    if resp.starts_with("250") {
        Ok(())
    } else {
        Err(format!("SignalFailed: {}", resp.trim()))
    }
}
