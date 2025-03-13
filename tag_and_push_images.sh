#!/bin/bash

# DJ Bot Script for Versioning and Docker Operations

# Function to prompt for a version number
get_version() {
    read -p "Please provide a version number for the DJ bot: " version
    if [[ -z "$version" ]]; then
        echo "Version number is required. Exiting."
        exit 1
    fi
}

# Function to build Docker image if requested
build_docker_image() {
    echo "Would you like to build the Docker image for the DJ bot before tagging and pushing?"
    echo "1. Yes"
    echo "2. No"
    read -p "Enter your choice (1-2): " build_choice

    case "$build_choice" in
        1)
            echo "Building Docker image for DJ bot..."
            docker-compose -f ./config/other_configs/docker-compose.yml build
            echo "Build completed."
            ;;
        2)
            echo "Skipping build."
            ;;
        *)
            echo "Invalid choice. Skipping build."
            ;;
    esac
}

# Function to tag and push the DJ bot image
tag_and_push_dj_bot() {
    image_name="$1"
    version="$2"

    docker tag "$image_name" "italiandogs/${image_name}:$version"
    docker tag "$image_name" "italiandogs/${image_name}:latest"
    echo "Tagged DJ bot with $version and latest"

    docker push "italiandogs/${image_name}:$version"
    docker push "italiandogs/${image_name}:latest"
    echo "Pushed DJ bot with $version and latest"
}

# Main script execution
get_version
build_docker_image
tag_and_push_dj_bot "dj-retrieval-bot" "$version"

echo "DJ bot Docker image operations completed."
