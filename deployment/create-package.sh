#!/bin/bash
set -e

echo "Creating deployment package for Content Assistant..."

# Create temporary directory
TEMP_DIR=$(mktemp -d)
PACKAGE_NAME="content-assistant-deploy"

echo "Temporary directory: $TEMP_DIR"

# Copy application files
echo "Copying application files..."
mkdir -p "$TEMP_DIR/$PACKAGE_NAME"
cp -r src "$TEMP_DIR/$PACKAGE_NAME/"
cp -r config "$TEMP_DIR/$PACKAGE_NAME/"
cp -r tools "$TEMP_DIR/$PACKAGE_NAME/"
cp requirements.txt "$TEMP_DIR/$PACKAGE_NAME/"
cp setup.sh "$TEMP_DIR/$PACKAGE_NAME/"
cp .env.example "$TEMP_DIR/$PACKAGE_NAME/"

# Copy deployment scripts
echo "Copying deployment scripts..."
cp -r deployment "$TEMP_DIR/$PACKAGE_NAME/"

# Create directories for data and logs
mkdir -p "$TEMP_DIR/$PACKAGE_NAME/data/memory"
mkdir -p "$TEMP_DIR/$PACKAGE_NAME/logs"
mkdir -p "$TEMP_DIR/$PACKAGE_NAME/profiles/active"

# Create .gitkeep files
touch "$TEMP_DIR/$PACKAGE_NAME/data/memory/.gitkeep"
touch "$TEMP_DIR/$PACKAGE_NAME/logs/.gitkeep"
touch "$TEMP_DIR/$PACKAGE_NAME/profiles/active/.gitkeep"

# Create tarball
echo "Creating tarball..."
cd "$TEMP_DIR"
tar -czf "$PACKAGE_NAME.tar.gz" "$PACKAGE_NAME"

# Move to current directory
mv "$PACKAGE_NAME.tar.gz" "$OLDPWD/"

# Cleanup
rm -rf "$TEMP_DIR"

echo "✓ Deployment package created: $PACKAGE_NAME.tar.gz"
echo "  Size: $(du -h $PACKAGE_NAME.tar.gz | cut -f1)"
