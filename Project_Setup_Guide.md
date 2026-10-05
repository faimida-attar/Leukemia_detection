# Complete Setup Guide: How to Run the Leukemia Detection Project on a New Laptop

This is a beginner-friendly, step-by-step guide to setting up and running your project on another laptop for your PhD Defense.

---

## STEP 1: Copy the Project to the New Laptop
1. Get a Pen Drive or Portable Hard Drive.
2. Copy the **entire** project folder: `leukemia_detection Resnet50 +Densenet 50` from your current laptop.
3. Paste this entire folder onto the Desktop (or Documents) of the new laptop.

---

## STEP 2: Install Required Software on the New Laptop

You need two basic software installed on the new laptop: **Python** and **VS Code**.

### 1. Install Python (If not already installed)
1. Open Google Chrome on the new laptop.
2. Go to `python.org/downloads`.
3. Download the latest Python version for Windows (e.g., Python 3.10 or 3.11).
4. Run the installer.
5. **VERY IMPORTANT:** On the very first installation screen, look at the bottom and check the box that says:
   **"Add Python to PATH"** or **"Add python.exe to PATH"**. (Do NOT skip this!)
6. Click "Install Now" and finish the setup.

### 2. Install Visual Studio Code (VS Code)
1. Go to `code.visualstudio.com`.
2. Download and install VS Code for Windows.
3. Open VS Code, go to the **Extensions** tab (the blocks icon on the left side).
4. Search for **"Live Server"** (by Ritwick Dey) and click **Install**. (This is needed to run your frontend UI easily).
5. Search for **"Python"** (by Microsoft) and click **Install**.

---

## STEP 3: Open the Project in VS Code
1. Open **VS Code**.
2. Go to `File` > `Open Folder...`
3. Select your main folder: `leukemia_detection Resnet50 +Densenet 50` -> `leukemia_detection` and click **Select Folder**.
   *(Make sure you can see the `backend` and `frontend` folders on the left panel in VS Code).*

---

## STEP 4: Install Python Libraries (Backend Setup)
Your backend (AI Model) needs some Python packages like PyTorch, Flask, OpenCV, etc., to run.

1. In VS Code, click on the top menu: `Terminal` > `New Terminal`.
2. A terminal box will open at the bottom.
3. First, you need to go inside the backend folder. Type this command and press Enter:
   ```bash
   cd backend
   ```
4. Now, install all the required libraries by typing this command and pressing Enter:
   ```bash
   pip install -r requirements.txt
   ```
   *(Wait for 5-10 minutes. It will download heavy libraries like torch, torchvision. Keep the internet connected.)*

---

## STEP 5: Run the Backend (The AI Brain)
Once all installations are complete, you need to start the backend server.

1. In the same terminal (make sure it says `\backend>` at the end of the line), type:
   ```bash
   python app.py
   ```
2. Press Enter.
3. Wait for a few seconds. You will see messages saying "Model loaded successfully".
4. Finally, you should see a line that says something like:
   `* Running on http://127.0.0.1:5000`
   *(This means your backend AI is now active and waiting for images).*
5. **DO NOT CLOSE THIS TERMINAL.** Leave it running in the background.

---

## STEP 6: Run the Frontend (The UI / Website)
Now you need to start the user interface so you can upload images.

1. In the left panel of VS Code, open the `frontend` folder.
2. Find the file named `index.html` (or whatever your main HTML file is named).
3. **Right-click** on `index.html`.
4. Click on **"Open with Live Server"**.
5. Your default web browser (Chrome/Edge) will automatically open and show your beautiful Leukemia Detection Website!

---

## STEP 7: Test the Project
1. The website is open in your browser.
2. The backend terminal in VS Code is running.
3. Click "Upload" on the website, select a test image (e.g., an AML or Normal slide).
4. Click "Predict" or "Submit".
5. Within seconds, it will show the Prediction, PSNR (35+ dB), and the Grad-CAM Heatmap.

**You are now fully ready to give your presentation!**

---

### Troubleshooting (In case of errors on stage):
- **Error: "pip is not recognized"** → Python was installed without checking "Add to PATH". Uninstall Python and reinstall it, making sure to check that box.
- **Error: "ModuleNotFoundError"** → You forgot to run `pip install -r requirements.txt` inside the `backend` folder.
- **Frontend says "Failed to fetch" or "Server Error"** → Your backend terminal has stopped or you forgot to run `python app.py`. Restart the backend terminal.
