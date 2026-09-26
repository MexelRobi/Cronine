#!/bin/bash

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}   Cronine Standalone Build Compiler     ${NC}"
echo -e "${BLUE}=========================================${NC}"

if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    elif [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        echo -e "${RED}[!] Virtual environment not found. Please create one first.${NC}"
        exit 1
    fi
fi

if [ ! -f ".venv/bin/pyinstaller" ]; then
    echo -e "${YELLOW}[*] PyInstaller missing inside local venv. Installing...${NC}"
    .venv/bin/pip install pyinstaller
fi

echo -e "${BLUE}[*] Compiling full standalone executable...${NC}"

.venv/bin/pyinstaller --onefile \
            --clean \
            --name "cronine" \
            --collect-binaries "llama_cpp" \
            --collect-data "llama_cpp" \
            --collect-all "textual" \
            --collect-all "huggingface_hub" \
            --copy-metadata "llama_cpp_python" \
            --copy-metadata "huggingface_hub" \
            --copy-metadata "textual" \
            app.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}[+] Build successful!${NC}"
    echo -e "${GREEN}[+] Your standalone binary is ready at: ${YELLOW}dist/cronine${NC}"
    echo -e "${BLUE}=========================================${NC}"
else
    echo -e "${RED}[!] Build failed.${NC}"
    exit 1
fi
