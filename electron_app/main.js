const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');

let pyProc = null;
let mainWindow = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false
    }
  });

  // Streamlit runs on localhost:8501 by default
  mainWindow.loadURL('http://localhost:8501');

  mainWindow.on('closed', () => {
    mainWindow = null;
    if (pyProc) pyProc.kill();
  });
}

app.on('ready', () => {
  // Launch Streamlit
  pyProc = spawn('streamlit', ['run', 'Music-Explorer.py'], {
    cwd: __dirname + '/../',
    shell: true
  });

  pyProc.stdout.on('data', (data) => {
    console.log(`stdout: ${data}`);
  });

  pyProc.stderr.on('data', (data) => {
    console.error(`stderr: ${data}`);
  });

  createWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
