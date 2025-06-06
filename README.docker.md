# Using Docker with NHL AI Agent

This document explains how to use Docker to run the NHL AI Agent across different operating systems.

## Installing Docker

### macOS
1. Install Docker Desktop for Mac:
   - Visit [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop)
   - Download the macOS installer (.dmg file)
   - Open the downloaded .dmg file and drag Docker to your Applications folder
   - Open Docker from your Applications folder
   - Wait for Docker to start (you'll see the whale icon in your menu bar)

### Windows
1. Install Docker Desktop for Windows:
   - Visit [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)
   - Download the Windows installer (.exe file)
   - Run the installer and follow the prompts
   - Ensure WSL 2 is installed if prompted (follow the instructions provided)
   - Start Docker Desktop from the Start menu
   - Wait for Docker to start (you'll see the whale icon in your system tray)

### Verifying Installation
After installation, open a terminal (macOS) or command prompt (Windows) and run:
```
docker --version
docker compose version
```

You should see version information for both commands.

## Getting Started

1. Clone the repository:
   ```
   git clone <repository-url>
   cd NHL_AI_Agent
   ```

2. Configure environment variables:
   - Copy the example environment file: `cp .env.example .env`
   - Edit `.env` file with your credentials (MySQL and OpenAI API key)

3. Build and start the Docker container:
   ```
   docker compose up -d
   ```
   Note: Newer Docker versions use `docker compose` instead of `docker-compose`

4. Access the application:
   - Open your browser and navigate to `http://localhost:8501`

5. Stop the application:
   ```
   docker compose down
   ```

## Development with Docker

For development, the Docker configuration mounts the `src` and `data` directories as volumes, allowing you to make changes to the code without rebuilding the container.

After making changes to your code, the Streamlit application will automatically reload.

## Troubleshooting

- If you encounter permission issues with mounted volumes on Linux, you may need to adjust permissions:
  ```
  sudo chown -R $USER:$USER src data
  ```

- If the container fails to start, check the logs:
  ```
  docker compose logs
  ```

- If your API keys or database connection aren't working, make sure your `.env` file is properly configured and the container can access it.

## Building for Production

To build a production-ready image:

```
docker build -t nhl-ai-agent:latest .
```

## Cross-Platform Development

This Docker setup ensures consistent behavior across macOS, Windows, and Linux environments, resolving dependency and compatibility issues between team members using different operating systems. 


## Misc Commands
To take down the docker container, rebuild it and start it
`docker compose down && docker compose build && docker compose up -d`


To remove all cached items and rebuild. 
NOTE: This removes everything cached with docker, regardless of project.
TODO: Update command to only remove nhl-ai-agent related content
```
docker compose down
docker system prune -a --volumes
docker compose build --no-cache
docker compose up -d
```