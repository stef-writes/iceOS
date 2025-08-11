#!/usr/bin/env bash
set -euo pipefail

# Usage: scripts/publish_images.sh <registry> <version>
# Example: scripts/publish_images.sh ghcr.io/yourorg 0.1.0

REGISTRY=${1:-}
VERSION=${2:-}
if [ -z "$REGISTRY" ] || [ -z "$VERSION" ]; then
  echo "Usage: $0 <registry> <version>" >&2
  exit 1
fi

IMAGE_API="$REGISTRY/ice-api"

# Ensure buildx
if ! docker buildx version >/dev/null 2>&1; then
  echo "docker buildx is required" >&2
  exit 1
fi

# Create builder if missing
if ! docker buildx inspect iceos >/dev/null 2>&1; then
  docker buildx create --name iceos --use >/dev/null
fi

echo "Building and pushing $IMAGE_API:$VERSION and :latest (linux/amd64,linux/arm64)"

docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t "$IMAGE_API:$VERSION" \
  -t "$IMAGE_API:latest" \
  -f Dockerfile \
  --push .
