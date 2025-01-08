# 📖 Complete Installation Guide

## 📋 Prerequisites

1. [Comfyui](https://github.com/comfyanonymous/ComfyUI) please install and configure for use.
    - Please enable --listen on your comfyui server. 
    - example: ``.\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build --listen``
2. Launch Comfyui and load workflow.json from required_files and install missing nodes.
   - If you are new or new installation please download [comfyui manager](https://github.com/ltdrdata/ComfyUI-Manager) before loading this workflow
   - From your web browser with ComfyUI loaded, click Workflow on top bar and select Open.  Navigate to your `\FluxComfyDiscordbot\required_files` directory and select `workflow.json`.  Ignore the "Missing Node Types" error.  In ComfyUI, choose "Manager" button on top right and select "Install Missing Custom Nodes".  Check the boxes for all items and choose "Install" on bottom left.  Once all are installed, restart ComfyUI.  The first restart of ComfyUI might take a few minutes after this install.

4. Ensure you have Python 3.x installed on your system. You can download it from [python.org](https://www.python.org/downloads/).

5. Install the required dependencies using the requirements.txt file: 
 ```pip install -r requirements.txt```
6. To get Redux working properly you will need to open Redux.json and Reduxprompt.json and install the missing nodes.
   - depending on your setup you may need to edit the json files to select the version of dev flux you are using. 
   - In redux.json find and change the name to your checkpoint name.
``` 
      "61": {
    "inputs": {
      "unet_name": "fluxFusionV24StepsGGUFNF4_V2Fp16.safetensors",
      "weight_dtype": "fp8_e4m3fn"
    },
    "class_type": "UNETLoader"
  },
```  
   - in reduxprompt.json find and change the name to your checkpoint name.
```
 "12": {
    "inputs": {
      "unet_name": "fluxFusionV24StepsGGUFNF4_V2Fp16.safetensors",
      "weight_dtype": "fp8_e4m3fn"
    },
    "class_type": "UNETLoader"
  },
```
   - download and install redux models manually **requires authentication on HF cannot be automated**
   - [Flux.1-Redux-dev](https://huggingface.co/black-forest-labs/FLUX.1-Redux-dev/tree/main) - place in ComfyUI/models/style_models
   - [sigclip_vision_384](https://huggingface.co/Comfy-Org/sigclip_vision_384/blob/main/sigclip_vision_patch14_384.safetensors) - place in ComfyUI/models/clip_vision folder
## 🔧 Installation Steps

### 1️⃣ ComfyUI Setup
1. Ensure ComfyUI is properly installed
2. Verify your installation directory structure:
   ```
   Example: 
   C:/Comfyui_windows_portable/ComfyUI/
   ```

### 2️⃣ Bot Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/nvmax/FluxComfyDiscordbot
   ```

2. **Run Setup Tool**
   ```bash
   python setup.py
   ```
   The setup tool will:
   - Copy required files needed to run
   - Setup your .env file with variables specified
   



### 3️⃣ Discord Bot Setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications). 

 * Click on "New Application" and give your bot a name. 
 * Once created, go to the "Bot" tab in the left sidebar. 
 * Click "Add Bot" to create a bot user for your application.
 * Under the bot's username, you'll see a "Token" section. Click "Copy" to copy your bot token. Keep this token secret and secure.
 * click Bot on the left side, In the "Privileged Gateway Intents" section, enable the following intents:
   * Presence Intent
   * Server Members Intent
   * Message Content Intent
* Go to the "OAuth2" tab in the left sidebar.
* In the "Scopes" section, select "bot".
* In the "Bot Permissions" section, select the permissions your bot needs. At minimum, it will need:- 
	* Send Messages
  * Manage Messages
	* Embed Links
	* Attach Files
	* Read Message History
	* Use Slash Commands

2. Copy the generated OAuth2 URL at the bottom of the "Scopes" section. 

3. Open a new browser tab, paste the URL, and select the server where you want to add the bot.

### 4️⃣ Verification Steps

After installation, verify:
- All dependencies are installed
- Workflow loads correctly
- Bot connects to Discord
- Commands are responsive

## 🔍 Post-Installation

### Testing the Installation
1. Start the bot:
   ```bash
   python bot.py
   ```
2. Try basic commands in Discord
3. Verify image generation works

### Common Issues
- Check [Troubleshooting Guide](troubleshooting.md) for common problems
- Verify file permissions
- Confirm Python version compatibility

## 📚 Next Steps

- [Configure your bot](configuration.md)
- [Learn available commands](commands.md)
- [Join our Discord community](https://discord.gg/your-invite-link)

## 🆘 Need Help?

- Check our [Troubleshooting Guide](troubleshooting.md)
- Join our [Discord Server](https://discord.gg/V3pRgtzjsN)
- Open an [Issue](https://github.com/nvmax/FluxComfyDiscordbot/issues)
