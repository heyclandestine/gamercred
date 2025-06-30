#!/usr/bin/env python3
"""
Build script for Gamer Cred Desktop
Compiles the Python app into a Windows executable
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def install_requirements():
    """Install required packages for building"""
    print("Installing build requirements...")
    
    requirements = [
        "pyinstaller",
        "psutil",
        "requests"
    ]
    
    for req in requirements:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", req])
            print(f"✓ Installed {req}")
        except subprocess.CalledProcessError:
            print(f"✗ Failed to install {req}")
            return False
    
    return True

def build_executable():
    """Build the executable using PyInstaller"""
    print("Building executable...")
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",                    # Single executable file
        "--windowed",                   # No console window
        "--name=GamerCredDesktop",      # Executable name
        "--icon=assets/icon.ico",       # Icon (if available)
        "--add-data=assets;assets",     # Include assets folder
        "--hidden-import=tkinter",
        "--hidden-import=psutil",
        "--hidden-import=requests",
        "gamer_cred_desktop.py"
    ]
    
    try:
        subprocess.check_call(cmd)
        print("✓ Executable built successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Build failed: {e}")
        return False

def create_installer():
    """Create a simple installer script"""
    print("Creating installer...")
    
    installer_script = """@echo off
echo Installing Gamer Cred Desktop...
echo.

REM Create program directory
if not exist "%PROGRAMFILES%\\GamerCredDesktop" mkdir "%PROGRAMFILES%\\GamerCredDesktop"

REM Copy executable
copy "dist\\GamerCredDesktop.exe" "%PROGRAMFILES%\\GamerCredDesktop\\"

REM Create desktop shortcut
powershell "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\\Desktop\\Gamer Cred Desktop.lnk'); $Shortcut.TargetPath = '%PROGRAMFILES%\\GamerCredDesktop\\GamerCredDesktop.exe'; $Shortcut.Save()"

REM Create start menu shortcut
if not exist "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Gamer Cred Desktop" mkdir "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Gamer Cred Desktop"
powershell "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Gamer Cred Desktop\\Gamer Cred Desktop.lnk'); $Shortcut.TargetPath = '%PROGRAMFILES%\\GamerCredDesktop\\GamerCredDesktop.exe'; $Shortcut.Save()"

echo.
echo Installation complete!
echo Gamer Cred Desktop has been installed to:
echo   - %PROGRAMFILES%\\GamerCredDesktop\\GamerCredDesktop.exe
echo.
echo Desktop and Start Menu shortcuts have been created.
echo.
pause
"""
    
    with open("install_gamer_cred_desktop.bat", "w") as f:
        f.write(installer_script)
    
    print("✓ Installer script created: install_gamer_cred_desktop.bat")

def create_portable_version():
    """Create a portable version"""
    print("Creating portable version...")
    
    portable_dir = "GamerCredDesktop_Portable"
    if os.path.exists(portable_dir):
        shutil.rmtree(portable_dir)
    
    os.makedirs(portable_dir)
    
    # Copy executable
    if os.path.exists("dist/GamerCredDesktop.exe"):
        shutil.copy("dist/GamerCredDesktop.exe", portable_dir)
    
    # Create README for portable version
    readme_content = """Gamer Cred Desktop - Portable Version

This is a portable version of Gamer Cred Desktop that doesn't require installation.

USAGE:
1. Double-click GamerCredDesktop.exe to run
2. The app will create a settings.json file in the same directory
3. You can move this folder anywhere and run it

FEATURES:
- Game tracking and session logging
- Quick access to web app features
- No installation required
- Settings saved locally

For more information, visit: https://github.com/your-repo/gamer-cred-desktop
"""
    
    with open(f"{portable_dir}/README.txt", "w") as f:
        f.write(readme_content)
    
    print(f"✓ Portable version created in: {portable_dir}")

def main():
    """Main build process"""
    print("🎮 Gamer Cred Desktop - Build Script")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("gamer_cred_desktop.py"):
        print("Error: gamer_cred_desktop.py not found!")
        print("Please run this script from the desktop directory.")
        return
    
    # Install requirements
    if not install_requirements():
        print("Failed to install requirements. Exiting.")
        return
    
    # Build executable
    if not build_executable():
        print("Failed to build executable. Exiting.")
        return
    
    # Create installer
    create_installer()
    
    # Create portable version
    create_portable_version()
    
    print("\n" + "=" * 50)
    print("🎉 Build completed successfully!")
    print("\nFiles created:")
    print("- dist/GamerCredDesktop.exe (Main executable)")
    print("- install_gamer_cred_desktop.bat (Installer script)")
    print("- GamerCredDesktop_Portable/ (Portable version)")
    print("\nTo distribute:")
    print("1. Share the .exe file directly")
    print("2. Use the installer script for system-wide installation")
    print("3. Share the portable folder for no-install usage")

if __name__ == "__main__":
    main() 