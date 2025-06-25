#!/bin/bash

############################################################################
# Script to build the Docker image using Docker Buildx and push to DockerHub.
#
# Instructions:
# 1. Set the DOCKER_USERNAME to your DockerHub username
# 2. Set the IMAGE_NAME and IMAGE_TAG variables to the desired values.
# 3. Ensure Docker Buildx is installed and configured.
# 4. Run 'docker buildx create --use' before executing this script.
# 5. Make sure you're logged in to DockerHub: 'docker login'
#
# This script builds a multi-platform Docker image for linux/amd64 and linux/arm64.
# The image is tagged and pushed to DockerHub.
############################################################################

# Exit immediately if a command exits with a non-zero status.
set -e

CURR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="$(dirname ${CURR_DIR})"
DOCKER_FILE="Dockerfile"

# DockerHub configuration - CHANGE THIS TO YOUR DOCKERHUB USERNAME
DOCKER_USERNAME="akhanbakhitov777"
IMAGE_NAME="crafty"
IMAGE_TAG="latest"

# Full image name for DockerHub
FULL_IMAGE_NAME="${DOCKER_USERNAME}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "Building and pushing image: $FULL_IMAGE_NAME"
echo "Platforms: linux/amd64,linux/arm64"

# Check if buildx builder exists, if not create one
if ! docker buildx ls | grep -q "multiarch"; then
    echo "Creating buildx builder..."
    docker buildx create --name multiarch --use
else
    echo "Using existing buildx builder..."
    docker buildx use multiarch
fi

echo "Running: docker buildx build --platform=linux/amd64,linux/arm64 -t $FULL_IMAGE_NAME -f $DOCKER_FILE $WS_ROOT --push"
docker buildx build --platform=linux/amd64,linux/arm64 -t $FULL_IMAGE_NAME -f $DOCKER_FILE $WS_ROOT --push

echo "Successfully built and pushed $FULL_IMAGE_NAME to DockerHub!"
echo "You can pull it with: docker pull $FULL_IMAGE_NAME"

# Автоматический trigger для Render.com
if [ ! -z "$RENDER_DEPLOY_HOOK" ]; then
    echo "============================================"
    echo "Triggering Render.com deployment..."
    echo "Deploy Hook URL: $RENDER_DEPLOY_HOOK"
    echo "============================================"
    
    # Выполняем запрос с подробными логами
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}\nTOTAL_TIME:%{time_total}" -X POST "$RENDER_DEPLOY_HOOK")
    
    # Парсим ответ
    HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
    TOTAL_TIME=$(echo "$RESPONSE" | grep "TOTAL_TIME:" | cut -d: -f2)
    BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/,$d')
    
    echo "Response Body: $BODY"
    echo "HTTP Status Code: $HTTP_CODE"
    echo "Request Time: ${TOTAL_TIME}s"
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✅ Deployment triggered successfully!"
        # Пытаемся извлечь deploy ID из ответа
        DEPLOY_ID=$(echo "$BODY" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
        if [ ! -z "$DEPLOY_ID" ]; then
            echo "🚀 Deploy ID: $DEPLOY_ID"
            echo "📊 Check deployment status at: https://dashboard.render.com"
        fi
    else
        echo "❌ Failed to trigger deployment. HTTP Status: $HTTP_CODE"
        echo "Response: $BODY"
    fi
    echo "============================================"
else
    echo "⚠️  RENDER_DEPLOY_HOOK environment variable not set. Skipping deployment trigger."
fi
