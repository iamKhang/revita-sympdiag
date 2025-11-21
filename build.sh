#!/bin/bash
# Pull base image trước để tránh timeout
echo "Pulling base image..."
docker pull --platform linux/amd64 python:3.11-slim

# Build image
echo "Building image..."
docker buildx build --platform linux/amd64 -t iamhoangkhang/revita-sympdiag:latest --load .

# docker push iamhoangkhang/revita-sympdiag:latest
