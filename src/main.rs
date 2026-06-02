pub mod transport;
pub mod protocol;
pub mod storage;
pub mod runtime;

use std::thread::available_parallelism;
use transport::tcp::start_tcp;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let parallelism = available_parallelism()?.get();
    println!("Physical parallelism: {}", parallelism);
    println!("Starting FlashGate Engine TCP foundation on port 8080...");
    start_tcp().await?;
    Ok(())
}
