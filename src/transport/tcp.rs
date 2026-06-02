use tokio::net::TcpStream;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use crate::protocol::http1::HttpRequest;
use tokio::net::TcpListener;
use socket2::{Socket, Domain, Type, Protocol};

async fn handle_connection(mut stream: TcpStream) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let mut buffer = [0u8; 4096];
    loop {
        let bytes_read = stream.read(&mut buffer).await?;
        if bytes_read == 0 {
            break;
        }
        
        let req = HttpRequest::parse(&buffer[..bytes_read]);
        match req {
            Ok(request) => {
                let response = b"HTTP\x2f1.1 200 OK\r\nContent-Type: text\x2fplain\r\nContent-Length: 24\r\nServer: FlashGate\r\nConnection: keep-alive\r\n\r\nHello, FlashGate Engine!";
                stream.write_all(response).await?;
                stream.flush().await?;
                
                let mut keep_alive = true;
                for (name, value) in request.headers {
                    if name.eq_ignore_ascii_case("connection") && value.eq_ignore_ascii_case("close") {
                        keep_alive = false;
                        break;
                    }
                }
                if !keep_alive {
                    break;
                }
            }
            Err(_err) => {
                let response = b"HTTP\x2f1.1 400 Bad Request\r\nContent-Type: text\x2fplain\r\nContent-Length: 11\r\nServer: FlashGate\r\nConnection: close\r\n\r\nBad Request";
                stream.write_all(response).await?;
                stream.flush().await?;
                break;
            }
        }
    }
    Ok(())
}

pub async fn start_tcp() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let socket = Socket::new(Domain::IPV4, Type::STREAM, Some(Protocol::TCP))?;
    socket.set_reuse_address(true)?;
    let address = "0.0.0.0:8080".parse::<std::net::SocketAddr>()?;
    socket.bind(&address.into())?;
    socket.listen(8192)?;
    let std_listener: std::net::TcpListener = socket.into();
    let listener = TcpListener::from_std(std_listener)?;
    
    loop {
        match listener.accept().await {
            Ok((stream, _)) => {
                tokio::spawn(async move {
                    let _ = handle_connection(stream).await;
                });
            }
            Err(_) => {
                tokio::time::sleep(std::time::Duration::from_millis(5)).await;
            }
        }
    }
}

