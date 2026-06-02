# FlashGate Engine

FlashGate Engine is a high-performance web server built with Rust and Tokio.

## Deployment on Azure VM

### 1. Provision VM and Open Ports
- Create an Azure VM (Ubuntu is recommended).
- In the Azure Network Security Group (NSG), add inbound port rules to open ports:
  - Port 8080 (FlashGate Engine)
  - Port 8081 (Nginx)

### 2. Set Up FlashGate Engine
- Install Rust and Cargo on the VM.
- Clone this repository.
- Navigate to the project directory and build the binary:
  ```bash
  cargo build --release
  ```
- Run the server:
  ```bash
  cargo run --release
  ```

### 3. Set Up Nginx
- Install Nginx:
  ```bash
  sudo apt update
  sudo apt install nginx
  ```
- Configure Nginx to serve a static response on port 8081.
- Restart Nginx:
  ```bash
  sudo systemctl restart nginx
  ```