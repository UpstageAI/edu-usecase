#!/bin/bash
# CTDMate Fine-tuned Model Downloader
# Downloads Llama 3.2-3B Term Normalizer (GGUF F16 format, ~6GB)

set -e  # Exit on error

echo "========================================================================"
echo "CTDMate Fine-tuned Model Downloader"
echo "========================================================================"
echo ""
echo "Model: Llama 3.2-3B Term Normalizer (F16 GGUF)"
echo "Size: ~6GB"
echo "Use: 약물/의학 용어 정규화 (Term Normalization)"
echo ""

# Determine project root (parent of ctdmate folder)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MODEL_DIR="$PROJECT_ROOT/models"
MODEL_PATH="$MODEL_DIR/llama-3.2-3B-term-normalizer-F16.gguf"

echo "Target path: $MODEL_PATH"
echo ""

# Check if model already exists
if [ -f "$MODEL_PATH" ]; then
    echo "✓ Model already exists at: $MODEL_PATH"
    echo ""
    read -p "Do you want to re-download? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted. Using existing model."
        exit 0
    fi
    rm -f "$MODEL_PATH"
fi

# Create models directory
mkdir -p "$MODEL_DIR"

echo "========================================================================"
echo "Download Options:"
echo "========================================================================"
echo "1. Manual download (copy/paste URL in browser)"
echo "2. Auto-download (gdown - recommended)"
echo ""
read -p "Select option (1-2): " CHOICE
echo ""

case $CHOICE in
    1)
        echo "========================================================================"
        echo "Manual Download Instructions:"
        echo "========================================================================"
        echo ""
        echo "1. Open this URL in your browser:"
        echo "   https://drive.google.com/file/d/1jXqPcVPB1MTnB_ao2BB6r45wEVtnTf0R/view?usp=sharing"
        echo ""
        echo "2. Click 'Download' button"
        echo ""
        echo "3. Move the downloaded file to:"
        echo "   $MODEL_PATH"
        echo ""
        echo "4. Verify the file size is ~6GB"
        echo ""
        exit 0
        ;;
    2)
        echo "Downloading from Google Drive..."
        echo ""

        # Google Drive file ID
        GDRIVE_ID="1jXqPcVPB1MTnB_ao2BB6r45wEVtnTf0R"
        GDRIVE_URL="https://drive.google.com/uc?export=download&id=$GDRIVE_ID"

        # Check if gdown is installed
        if command -v gdown &> /dev/null; then
            echo "✓ gdown found"
        else
            echo "Installing gdown..."
            pip install gdown
        fi

        # Download using gdown
        echo ""
        echo "Starting download (this may take several minutes for ~6GB file)..."
        gdown "$GDRIVE_URL" -O "$MODEL_PATH"

        if [ -f "$MODEL_PATH" ]; then
            FILE_SIZE=$(du -h "$MODEL_PATH" | cut -f1)
            echo ""
            echo "✓ Download complete!"
            echo "  Path: $MODEL_PATH"
            echo "  Size: $FILE_SIZE"
        else
            echo ""
            echo "✗ Download failed. Please try manual download (option 1)."
            exit 1
        fi
        ;;
    *)
        echo "Invalid option. Aborted."
        exit 1
        ;;
esac

echo ""
echo "========================================================================"
echo "Model Installation Complete!"
echo "========================================================================"
echo ""
echo "Usage:"
echo "  python pipeline.py  # Auto-loads fine-tuned model"
echo ""
echo "Or in code:"
echo "  from ctdmate.pipeline import CTDPipeline"
echo "  pipe = CTDPipeline(use_finetuned=True)  # Default"
echo ""
echo "To disable fine-tuned model:"
echo "  pipe = CTDPipeline(use_finetuned=False)  # Heuristic only"
echo ""
