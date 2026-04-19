#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"
mkdir -p .secrets

openssl genrsa -out .secrets/jwt_private_key.pem 2048
openssl rsa -in .secrets/jwt_private_key.pem -outform PEM -pubout -out .secrets/jwt_public_key.pem

chmod 600 .secrets/jwt_private_key.pem
chmod 600 .secrets/jwt_public_key.pem
