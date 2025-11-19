# Pi Photo Album

Turn any monitor into a digital photo frame using a Raspberry Pi.

![Image](https://github.com/user-attachments/assets/a3f1a5c7-bd16-488c-bb06-4a3bfaf60f3b)

## 🌟 Features

- 📸 Display photos as a slideshow from your Raspberry Pi
- 🔄 Real-time photo syncing across multiple users with AWS
- 🚀 Easy installation and setup
- 🌐 Simple Web interface for photo management
- 🔧 Configurable photo display settings

## 🚀 Setup Guide

### Prerequisites

- Raspberry Pi(s) with internet access and a monitor
- An AWS account

### Setting up the Cloud infrastructure

Follow the [admin/aws/onboard.md](admin/aws/onboard.md) for instructions to set up the AWS infrastructure.

Once setup, you are ready to onboard Raspberry Pi(s) into your photo album network.

### Installing the app

Follow the [Installation Guide](install.md) for instructions to install the app on your Raspberry Pi.

## 📐 Architecture

### Overall App Architecture

![Overall App Architecture](https://github.com/user-attachments/assets/fa5782d1-496e-43f5-8242-fad934d56a75)

- **Client Application** - Runs on Raspberry Pi, displays photos and syncs local filesystem with the cloud
- **Flask Web Server** - Web server for managing photos and settings
- **Event Consumer** - Background service for processing filesystem events from other users in the network
- **AWS Infrastructure** - Maintains a filesystem on the cloud and syncs changes between clients

### Client Side Architecture

![Client Side Architecture](https://github.com/user-attachments/assets/9d116ede-e2bd-4556-aacf-62c2bae6f673)

The client application consists of two main processes that work together to keep photos synchronized across all devices:

#### Web Server (Flask)

The web server serves the web page and API for managing photos:

- **Web Page** - A local web page for uploading and managing photos
- **REST API** - Endpoints for file operations (upload, delete, move, copy, rotate)
- **Slideshow Control** - Start/stop slideshow, configure display settings (speed, blend time, album selection)
- **Event Publishing** - When you make changes locally (upload, delete, etc.), the server pushes those events to AWS SQS so other devices can stay in sync
- **Server-Sent Events (SSE)** - Real-time updates to the UI when events are received from other users

#### Event Consumer Service

A background service that keeps your local photos in sync with changes made by other users:

- **Polls AWS SQS** - Continuously checks for filesystem events from other Raspberry Pis in the network
- **Applies Remote Changes** - When another user makes changes to a shared portion of the filesystem, this service forwards those events to the web server to apply the changes locally
- **Health Monitoring** - Monitors connectivity to both the web server and AWS, handling offline scenarios to help prevent losing events
- **Resync Logic** - If the device has been offline for an extended period, automatically triggers a full resynchronization with the cloud

## 💻 Development

### Prerequisites

- Python 3.11 or higher
- pip and virtualenv installed
- An AWS account

### Running from Source

1. Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

1. Install dependencies:
    ```bash
    pip install -e ".[dev]"
    ```

1. Set up environment variables:
    - See [install.md](install.md#5-setup-environment-variable-file) for getting the required environment variables.
    - For development, you may create the `.env` file at the project root or in `~/.config/pi-photo-album/`.

1. Run the application:
    ```bash
    # Normal mode
    python -m app.server

    # Debug mode
    FLASK_DEBUG=true python -m app.server
    ```

### Testing

Run the test suite:
```bash
python -m pytest
```

### Building a Release
1. Bump the version in [pyproject.toml](pyproject.toml).

1. Create a distribution package:
    ```bash
    python -m build
    ```

1. Create a GitHub release:
    ```bash
    gh release create v<VERSION> dist/pi_photo_album-<VERSION>.tar.gz
    ```

## Project Structure

```
pi-photo-album/
├── app/                   # Main application code
│   ├── cloud_clients/     # Cloud provider client wrappers
│   ├── config/            # Simple app config library
│   ├── event_consumer/    # Event processing service
│   ├── routes/            # API route handlers
│   ├── static/            # Static files (JS, CSS, images)
│   ├── utils/             # Utility functions
│   ├── templates/         # Web page templates
│   └── tests/             # Test suite for web server
├── admin/                 # Infrastructure and admin tools
└──   └── aws/             # Terraform AWS configuration
```
