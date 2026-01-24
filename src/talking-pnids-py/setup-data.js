const fs = require('fs');
const path = require('path');

const scriptDir = __dirname;
const jsDataDir = path.join(scriptDir, '..', 'talking-pnids-js', 'data');
const pyDataDir = path.join(scriptDir, 'data');

console.log('Setting up data directory...\n');

// Create data directories
const dirs = ['pdfs', 'jsons', 'mds'];
dirs.forEach(dir => {
  const dirPath = path.join(pyDataDir, dir);
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
    console.log(`Created directory: ${dirPath}`);
  }
});

// Copy files if source exists
if (fs.existsSync(jsDataDir)) {
  dirs.forEach(dir => {
    const srcDir = path.join(jsDataDir, dir);
    const destDir = path.join(pyDataDir, dir);
    
    if (fs.existsSync(srcDir)) {
      console.log(`Copying ${dir}...`);
      const files = fs.readdirSync(srcDir);
      files.forEach(file => {
        const srcFile = path.join(srcDir, file);
        const destFile = path.join(destDir, file);
        fs.copyFileSync(srcFile, destFile);
        console.log(`  Copied: ${file}`);
      });
    }
  });
  
  console.log('\nData files copied successfully!');
  console.log('\nFiles in data directory:');
  dirs.forEach(dir => {
    const dirPath = path.join(pyDataDir, dir);
    if (fs.existsSync(dirPath)) {
      const files = fs.readdirSync(dirPath);
      console.log(`\n${dir}/ (${files.length} files):`);
      files.slice(0, 5).forEach(file => console.log(`  - ${file}`));
    }
  });
} else {
  console.error(`\nError: JS project data directory not found at ${jsDataDir}`);
  console.error('Please ensure the talking-pnids-js project exists in the parent directory');
  process.exit(1);
}
