const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  blue: '\x1b[34m',
  yellow: '\x1b[33m',
};

console.log(`${colors.blue}Starting Talking P&IDs Application...${colors.reset}\n`);

const scriptDir = __dirname;
const backendDir = path.join(scriptDir, 'backend');
const frontendDir = path.join(scriptDir, 'frontend');

let backendProcess = null;
let frontendProcess = null;

// Cleanup function
function cleanup() {
  console.log(`\n${colors.yellow}Shutting down servers...${colors.reset}`);
  if (backendProcess) {
    backendProcess.kill();
  }
  if (frontendProcess) {
    frontendProcess.kill();
  }
  process.exit();
}

// Handle Ctrl+C
process.on('SIGINT', cleanup);
process.on('SIGTERM', cleanup);

// Start backend
console.log(`${colors.green}Starting backend server...${colors.reset}`);
const isWindows = process.platform === 'win32';
const venvPath = path.join(backendDir, 'venv');
const pythonCmd = isWindows 
  ? path.join(venvPath, 'Scripts', 'python.exe')
  : path.join(venvPath, 'bin', 'python');

// Check if venv exists, if not create it
if (!fs.existsSync(venvPath)) {
  console.log(`${colors.yellow}Creating virtual environment...${colors.reset}`);
  const venvProcess = spawn(isWindows ? 'python' : 'python3', ['-m', 'venv', 'venv'], {
    cwd: backendDir,
    stdio: 'inherit',
  });
  venvProcess.on('close', (code) => {
    if (code === 0) {
      startBackend();
    }
  });
} else {
  startBackend();
}

function startBackend() {
  // Check if dependencies are installed
  const depsFile = path.join(venvPath, '.deps_installed');
  const pipCmd = isWindows 
    ? path.join(venvPath, 'Scripts', 'pip.exe')
    : path.join(venvPath, 'bin', 'pip');
  
  if (!fs.existsSync(depsFile)) {
    console.log(`${colors.yellow}Installing backend dependencies...${colors.reset}`);
    const installProcess = spawn(pipCmd, ['install', '-r', 'requirements.txt', '--upgrade'], {
      cwd: backendDir,
      stdio: 'inherit',
    });
    
    installProcess.on('close', (code) => {
      if (code === 0) {
        fs.writeFileSync(depsFile, '');
        runBackend();
      }
    });
  } else {
    // Always upgrade openai to fix compatibility issues
    console.log(`${colors.yellow}Upgrading OpenAI library...${colors.reset}`);
    const upgradeProcess = spawn(pipCmd, ['install', '--upgrade', 'openai'], {
      cwd: backendDir,
      stdio: 'inherit',
    });
    
    upgradeProcess.on('close', (code) => {
      runBackend();
    });
  }
}

function runBackend() {
  backendProcess = spawn(pythonCmd, ['main.py'], {
    cwd: backendDir,
    stdio: 'inherit',
    shell: isWindows,
  });

  backendProcess.on('error', (err) => {
    console.error(`${colors.yellow}Backend error: ${err.message}${colors.reset}`);
    console.log(`${colors.yellow}Trying with 'python' command...${colors.reset}`);
    backendProcess = spawn('python', ['main.py'], {
      cwd: backendDir,
      stdio: 'inherit',
      shell: true,
    });
  });

  console.log(`${colors.green}Backend started (PID: ${backendProcess.pid})${colors.reset}\n`);

  // Wait a bit for backend to start, then start frontend
  setTimeout(() => {
    startFrontend();
  }, 2000);
}

function startFrontend() {
  console.log(`${colors.green}Starting frontend server...${colors.reset}`);
  
  // Check if node_modules exists
  const nodeModulesPath = path.join(frontendDir, 'node_modules');
  if (!fs.existsSync(nodeModulesPath)) {
    console.log(`${colors.yellow}Installing frontend dependencies...${colors.reset}`);
    const installProcess = spawn('npm', ['install'], {
      cwd: frontendDir,
      stdio: 'inherit',
      shell: true,
    });
    
    installProcess.on('close', (code) => {
      if (code === 0) {
        runFrontend();
      }
    });
  } else {
    runFrontend();
  }
}

function runFrontend() {
  frontendProcess = spawn('npm', ['run', 'dev'], {
    cwd: frontendDir,
    stdio: 'inherit',
    shell: true,
  });

  console.log(`${colors.green}Frontend started (PID: ${frontendProcess.pid})${colors.reset}\n`);

  console.log(`${colors.blue}========================================${colors.reset}`);
  console.log(`${colors.green}Both servers are running!${colors.reset}`);
  console.log(`${colors.blue}Backend:${colors.reset}  http://localhost:8000`);
  console.log(`${colors.blue}Frontend:${colors.reset} http://localhost:3000`);
  console.log(`${colors.blue}========================================${colors.reset}`);
  console.log(`${colors.yellow}Press Ctrl+C to stop both servers${colors.reset}\n`);
}
