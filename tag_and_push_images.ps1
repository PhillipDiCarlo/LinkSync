# DJ Bot Script for Versioning and Docker Operations

# Function to prompt for a version number
function GetVersion {
    $version = Read-Host "Please provide a version number for the DJ bot"
    if (-not $version) {
        Write-Host "Version number is required. Exiting."
        exit 1
    }
    return $version
}

# Function to build Docker image if requested
function BuildDockerImage {
    $buildChoice = @"
1. Yes
2. No
"@
    Write-Host "Would you like to build the Docker image for the DJ bot before tagging and pushing?"
    Write-Host $buildChoice
    $build = Read-Host "Enter your choice (1-2)"
    
    switch ($build) {
        1 {
            Write-Host "Building Docker image for DJ bot..."
            docker-compose -f .\config\other_configs\docker-compose.yml build
            Write-Output "Build completed."
        }
        2 {
            Write-Host "Skipping build."
        }
        Default {
            Write-Host "Invalid choice. Skipping build."
        }
    }
}

# Function to tag and push the DJ bot image
function TagAndPushDJBot($imageName, $version) {
    docker tag $imageName "italiandogs/${imageName}:$version"
    docker tag $imageName "italiandogs/${imageName}:$version"
    docker tag $imageName "italiandogs/${imageName}:latest"
    Write-Output "Tagged DJ bot with $version and latest"

    docker push "italiandogs/${imageName}:$version"
    docker push "italiandogs/${imageName}:latest"
    Write-Output "Pushed DJ bot with $version and latest"
}

# Main script execution
$version = GetVersion
BuildDockerImage
TagAndPushDJBot "dj-retrieval-bot" $version

Write-Host "DJ bot Docker image operations completed."
