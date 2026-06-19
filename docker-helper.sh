#!/bin/bash
# Docker helper script for OSS Compliance Web Application

set -e

# Configuration
IMAGE_NAME="oss-compliance-webapp"
REGISTRY="ghcr.io/jpurcell3/oss-scanner"
VERSION=${1:-latest}

echo "OSS Compliance Web Application - Docker Helper Script"
echo "======================================================"

# Function to build Docker image
build_image() {
    echo "Building Docker image..."
    docker build -t ${IMAGE_NAME}:${VERSION} .
    echo "✅ Image built: ${IMAGE_NAME}:${VERSION}"
}

# Function to run container
run_container() {
    echo "Running container..."
    docker run -d \
        -p 5001:5001 \
        --env-file .env \
        -v $(pwd)/reports:/app/reports \
        -v $(pwd)/uploads:/app/uploads \
        -v $(pwd)/cache:/app/cache \
        --name ${IMAGE_NAME} \
        ${IMAGE_NAME}:${VERSION}
    echo "✅ Container started: ${IMAGE_NAME}"
    echo "🌐 Access at: http://localhost:5001"
}

# Function to stop container
stop_container() {
    echo "Stopping container..."
    docker stop ${IMAGE_NAME} || true
    docker rm ${IMAGE_NAME} || true
    echo "✅ Container stopped and removed"
}

# Function to login to GitHub Container Registry
login_ghcr() {
    echo "Logging in to GitHub Container Registry..."
    echo "Enter your GitHub personal access token:"
    read -s TOKEN
    echo $TOKEN | docker login ghcr.io -u ${{ github.actor }} --password-stdin
    echo "✅ Logged in to ghcr.io"
}

# Function to tag for GitHub Container Registry
tag_ghcr() {
    echo "Tagging image for GitHub Container Registry..."
    docker tag ${IMAGE_NAME}:${VERSION} ${REGISTRY}:${VERSION}
    echo "✅ Tagged: ${REGISTRY}:${VERSION}"
}

# Function to push to GitHub Container Registry
push_ghcr() {
    echo "Pushing to GitHub Container Registry..."
    docker push ${REGISTRY}:${VERSION}
    echo "✅ Pushed: ${REGISTRY}:${VERSION}"
}

# Function to pull from GitHub Container Registry
pull_ghcr() {
    echo "Pulling from GitHub Container Registry..."
    docker pull ${REGISTRY}:${VERSION}
    echo "✅ Pulled: ${REGISTRY}:${VERSION}"
}

# Function to show logs
logs() {
    echo "Showing container logs..."
    docker logs -f ${IMAGE_NAME}
}

# Function to clean up
cleanup() {
    echo "Cleaning up Docker resources..."
    docker system prune -f
    echo "✅ Cleanup complete"
}

# Function to show help
show_help() {
    echo "Usage: ./docker-helper.sh [command] [version]"
    echo ""
    echo "Commands:"
    echo "  build       - Build Docker image"
    echo "  run         - Run container"
    echo "  stop        - Stop and remove container"
    echo "  login-ghcr  - Login to GitHub Container Registry"
    echo "  tag-ghcr    - Tag image for GitHub Container Registry"
    echo "  push-ghcr   - Push to GitHub Container Registry"
    echo "  pull-ghcr   - Pull from GitHub Container Registry"
    echo "  logs        - Show container logs"
    echo "  cleanup     - Clean up Docker resources"
    echo "  help        - Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./docker-helper.sh build"
    echo "  ./docker-helper.sh build v1.0"
    echo "  ./docker-helper.sh run"
    echo "  ./docker-helper.sh tag-ghcr v1.0"
    echo "  ./docker-helper.sh push-ghcr v1.0"
}

# Main script logic
case "${1:-help}" in
    build)
        build_image
        ;;
    run)
        run_container
        ;;
    stop)
        stop_container
        ;;
    login-ghcr)
        login_ghcr
        ;;
    tag-ghcr)
        tag_ghcr
        ;;
    push-ghcr)
        push_ghcr
        ;;
    pull-ghcr)
        pull_ghcr
        ;;
    logs)
        logs
        ;;
    cleanup)
        cleanup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        show_help
        exit 1
        ;;
esac