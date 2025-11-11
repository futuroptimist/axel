# Local LLM Setup Guide for Windows 11 + RTX 4090

This guide walks you through setting up a local LLM on your Windows 11 development machine with an RTX 4090 GPU for working on Axel and other Python projects.

## Why Run LLMs Locally?

- **Privacy**: Your code and prompts stay on your machine
- **Cost**: No API fees after initial setup
- **Speed**: GPU inference can be faster than API calls with network latency
- **Offline**: Work without internet connectivity
- **Experimentation**: Try different models and configurations freely

## Hardware Requirements

- **GPU**: RTX 4090 (24GB VRAM) - excellent for running 30B+ parameter models
- **RAM**: 32GB+ system RAM recommended
- **Storage**: 100GB+ free space for models
- **OS**: Windows 11 with latest updates

## Step 1: Install Prerequisites

### 1.1 Install CUDA Toolkit

1. Download CUDA Toolkit 12.x from [NVIDIA's website](https://developer.nvidia.com/cuda-downloads)
2. Run the installer and select "Express Installation"
3. Verify installation:
   ```powershell
   nvcc --version
   ```

### 1.2 Install Python

1. Download Python 3.11+ from [python.org](https://www.python.org/downloads/)
2. During installation, check "Add Python to PATH"
3. Verify:
   ```powershell
   python --version
   ```

### 1.3 Install Git

1. Download Git for Windows from [git-scm.com](https://git-scm.com/download/win)
2. Use default installation options
3. Verify:
   ```powershell
   git --version
   ```

## Step 2: Choose Your LLM Backend

You have three popular options for running local LLMs on Windows:

### Option A: Ollama (Recommended for Beginners)

**Pros**: Easiest setup, good model management, active development
**Cons**: Fewer configuration options

1. Download Ollama for Windows from [ollama.com](https://ollama.com/download)
2. Run the installer
3. Open PowerShell and pull a coding model:
   ```powershell
   ollama pull qwen2.5-coder:32b
   ```
4. Test it:
   ```powershell
   ollama run qwen2.5-coder:32b "Write a Python function to reverse a string"
   ```

### Option B: LM Studio

**Pros**: User-friendly GUI, easy model discovery, built-in chat interface
**Cons**: Less scriptable than CLI tools

1. Download LM Studio from [lmstudio.ai](https://lmstudio.ai/)
2. Install and launch the application
3. Browse models in the UI (look for `TheBloke/deepseek-coder-33B-instruct-GGUF` or similar)
4. Download a quantized model (Q4_K_M is a good balance)
5. Load the model and start the local server (Settings → Local Server)

### Option C: vLLM with WSL2

**Pros**: Best performance, most flexible, production-grade
**Cons**: More complex setup

1. Install WSL2:
   ```powershell
   wsl --install -d Ubuntu-22.04
   ```
2. Inside WSL2, install vLLM:
   ```bash
   pip install vllm
   ```
3. Run a model:
   ```bash
   python -m vllm.entrypoints.openai.api_server \
     --model deepseek-ai/deepseek-coder-33b-instruct \
     --gpu-memory-utilization 0.9
   ```

## Step 3: Recommended Models for Coding

For your RTX 4090 (24GB VRAM), these models work well:

| Model | Size | Best For | VRAM Usage |
|-------|------|----------|------------|
| **Qwen2.5-Coder-32B** | 32B | Python, general coding | ~20GB (Q4) |
| DeepSeek-Coder-33B | 33B | Multi-language code | ~20GB (Q4) |
| CodeLlama-34B | 34B | Code completion | ~21GB (Q4) |
| Phind-CodeLlama-34B | 34B | Detailed explanations | ~21GB (Q4) |
| Qwen2.5-Coder-14B | 14B | Fast responses | ~9GB (Q4) |

**Note**: Sizes shown are for 4-bit quantized models. Q4_K_M or Q4_0 quantization offers the best balance of quality and VRAM usage.

## Step 4: Integrate with Your IDE

### VS Code + Continue

1. Install the Continue extension from VS Code marketplace
2. Open Continue settings (Ctrl+Shift+P → "Continue: Open Config")
3. Configure for Ollama:
   ```json
   {
     "models": [{
       "title": "Qwen2.5 Coder",
       "provider": "ollama",
       "model": "qwen2.5-coder:32b"
     }],
     "tabAutocompleteModel": {
       "title": "Qwen2.5 Coder",
       "provider": "ollama",
       "model": "qwen2.5-coder:32b"
     }
   }
   ```

### VS Code + Cline (formerly Claude Dev)

1. Install Cline extension
2. Configure API settings to use Ollama endpoint: `http://localhost:11434`
3. Select your model from the dropdown

### Cursor IDE

1. Open Settings → Models
2. Add custom model pointing to `http://localhost:11434/v1`
3. Enter your model name (e.g., `qwen2.5-coder:32b`)

## Step 5: CLI Tools for Axel Development

### Aider - AI Pair Programming

```powershell
pip install aider-chat
```

Configure for Ollama:
```powershell
$env:OLLAMA_API_BASE="http://localhost:11434"
aider --model ollama/qwen2.5-coder:32b
```

Use with Axel:
```powershell
cd path\to\axel
aider --model ollama/qwen2.5-coder:32b
```

## Step 6: Performance Tuning

### Optimize GPU Settings

```powershell
# Set CUDA environment variables
$env:CUDA_VISIBLE_DEVICES="0"
$env:PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:512"
```

### Monitor GPU Usage

```powershell
# Install nvidia-smi monitoring
nvidia-smi -l 1  # Refresh every second
```

### Adjust Model Context Length

For Ollama:
```powershell
ollama run qwen2.5-coder:32b --ctx 8192
```

Longer context = more VRAM usage, but better understanding of large files.

## Step 7: Test with Axel

1. Clone Axel:
   ```powershell
   git clone https://github.com/futuroptimist/axel
   cd axel
   ```

2. Set up Python environment:
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   pip install -e . -r requirements.txt
   ```

3. Test the LLM on a simple task:
   ```powershell
   # Using Aider
   aider --model ollama/qwen2.5-coder:32b axel\repo_manager.py
   ```

   Then ask: "Explain the main purpose of this module"

## Troubleshooting

### GPU Not Detected

- Verify NVIDIA drivers are up to date
- Restart Ollama/LM Studio after driver updates
- Check: `nvidia-smi` shows your GPU

### Out of Memory Errors

- Try a smaller quantized model (Q4 instead of Q5)
- Reduce context window size
- Close other GPU-intensive applications
- Use a smaller model (14B instead of 32B)

### Slow Performance

- Ensure you're using GPU, not CPU (check with `nvidia-smi`)
- Try different quantization levels (Q4_K_M often fastest)
- Reduce context window size
- Check Windows power settings (set to "High Performance")

### Model Download Issues

- Use a VPN if downloads are blocked
- Download manually from HuggingFace and import to Ollama
- Check disk space (models can be 20GB+)

## Best Practices for Axel Development

1. **Use smaller context windows** when editing small files to speed up responses
2. **Keep model loaded** between sessions to avoid startup time
3. **Use specific prompts** referencing the codebase structure:
   - "In the `axel/` package..."
   - "Looking at tests/test_repo_manager.py..."
4. **Test incrementally** - use the LLM to suggest changes, then run tests locally
5. **Commit frequently** - LLMs work better with clean git history

## Next Steps

- Experiment with different models to find your favorite
- Set up custom system prompts for Python/testing
- Integrate with GitHub Copilot for hybrid approach
- Try fine-tuning on Axel's codebase (advanced)

## Resources

- [Ollama Documentation](https://github.com/ollama/ollama)
- [LM Studio Discord](https://discord.gg/lmstudio)
- [Continue Documentation](https://continue.dev/docs)
- [Aider Documentation](https://aider.chat/)
- [HuggingFace Models](https://huggingface.co/models?pipeline_tag=text-generation)

## Contributing

Found a better model or configuration? Open a PR to update this guide!
