#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

console.log('🎮 Gamer Cred Desktop Setup');
console.log('============================\n');

// Check if we're in the right directory
if (!fs.existsSync('package.json')) {
  console.error('❌ Error: package.json not found. Please run this script from the desktop directory.');
  process.exit(1);
}

// Check Node.js version
const nodeVersion = process.version;
const majorVersion = parseInt(nodeVersion.slice(1).split('.')[0]);
if (majorVersion < 16) {
  console.error('❌ Error: Node.js 16 or higher is required. Current version:', nodeVersion);
  process.exit(1);
}

console.log('✅ Node.js version:', nodeVersion);

// Install dependencies
console.log('\n📦 Installing dependencies...');
try {
  execSync('npm install', { stdio: 'inherit' });
  console.log('✅ Dependencies installed successfully');
} catch (error) {
  console.error('❌ Failed to install dependencies:', error.message);
  process.exit(1);
}

// Create assets directory if it doesn't exist
const assetsDir = path.join(__dirname, 'assets');
if (!fs.existsSync(assetsDir)) {
  fs.mkdirSync(assetsDir, { recursive: true });
  console.log('✅ Created assets directory');
}

// Create placeholder icon files
const iconFiles = [
  { name: 'icon.png', size: '512x512' },
  { name: 'icon.ico', size: 'Windows icon' },
  { name: 'icon.icns', size: 'macOS icon' },
  { name: 'tray-icon.png', size: '16x16' }
];

console.log('\n📁 Creating placeholder assets...');
iconFiles.forEach(icon => {
  const iconPath = path.join(assetsDir, icon.name);
  if (!fs.existsSync(iconPath)) {
    // Create a simple placeholder file
    fs.writeFileSync(iconPath, '');
    console.log(`✅ Created placeholder: ${icon.name}`);
  }
});

// Create .env.example if it doesn't exist
const envExamplePath = path.join(__dirname, '.env.example');
if (!fs.existsSync(envExamplePath)) {
  const envExample = `# Gamer Cred Desktop Configuration

# API Configuration
API_URL=https://gamercred.onrender.com

# Discord Configuration (if needed for local development)
DISCORD_CLIENT_ID=your_discord_client_id
DISCORD_CLIENT_SECRET=your_discord_client_secret

# Development Settings
NODE_ENV=development
DEBUG=false
`;
  
  fs.writeFileSync(envExamplePath, envExample);
  console.log('✅ Created .env.example file');
}

// Check if .env exists
const envPath = path.join(__dirname, '.env');
if (!fs.existsSync(envPath)) {
  console.log('\n⚠️  No .env file found. Creating one from .env.example...');
  try {
    fs.copyFileSync(envExamplePath, envPath);
    console.log('✅ Created .env file from .env.example');
    console.log('📝 Please edit .env file with your configuration');
  } catch (error) {
    console.error('❌ Failed to create .env file:', error.message);
  }
}

// Create build script
const buildScript = `#!/bin/bash
echo "Building Gamer Cred Desktop..."

# Build for current platform
npm run build

echo "Build complete! Check the dist/ folder for the executable."
`;

const buildScriptPath = path.join(__dirname, 'build.sh');
if (!fs.existsSync(buildScriptPath)) {
  fs.writeFileSync(buildScriptPath, buildScript);
  fs.chmodSync(buildScriptPath, '755');
  console.log('✅ Created build.sh script');
}

console.log('\n🎉 Setup complete!');
console.log('\nNext steps:');
console.log('1. Edit .env file with your configuration');
console.log('2. Run "npm run dev" to start in development mode');
console.log('3. Run "npm run build-win" to build for Windows');
console.log('4. Check the dist/ folder for the executable');
console.log('\nFor more information, see README.md'); 