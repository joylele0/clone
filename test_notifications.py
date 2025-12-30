#!/usr/bin/env python3
import sys
import os

print("=" * 60)
print("LMS NOTIFICATION SYSTEM DIAGNOSTIC")
print("=" * 60)

# Test 1: Check plyer installation
print("\n[1] Checking plyer installation...")
try:
    import plyer
    print("    ✓ plyer is installed")
    print(f"    Version: {plyer.__version__ if hasattr(plyer, '__version__') else 'unknown'}")
except ImportError:
    print("    ✗ plyer is NOT installed")
    print("    Install with: pip install plyer")
    sys.exit(1)

# Test 2: Check notification module
print("\n[2] Checking notification module...")
try:
    from plyer import notification
    print("    ✓ notification module available")
except ImportError as e:
    print(f"    ✗ Cannot import notification: {e}")
    sys.exit(1)

# Test 3: Check platform
print("\n[3] Checking platform...")
import platform
system = platform.system()
print(f"    Platform: {system}")
print(f"    Release: {platform.release()}")

# Test 4: Check display environment
print("\n[4] Checking display environment...")
if system == "Linux":
    display = os.environ.get('DISPLAY')
    wayland = os.environ.get('WAYLAND_DISPLAY')
    xdg = os.environ.get('XDG_SESSION_TYPE')
    
    print(f"    DISPLAY: {display or 'NOT SET'}")
    print(f"    WAYLAND_DISPLAY: {wayland or 'NOT SET'}")
    print(f"    XDG_SESSION_TYPE: {xdg or 'NOT SET'}")
    
    if not display and not wayland:
        print("    ✗ No display environment detected!")
        print("    OS notifications require a graphical desktop environment")
        print("    This appears to be a headless/server environment")
elif system == "Darwin":
    print("    macOS detected")
elif system == "Windows":
    print("    Windows detected")

# Test 5: Check notification backend
print("\n[5] Checking notification backend...")
try:
    from plyer.platforms import linux, macosx, win
    if system == "Linux":
        print("    Checking for notify-send...")
        result = os.system("which notify-send > /dev/null 2>&1")
        if result == 0:
            print("    ✓ notify-send found")
        else:
            print("    ✗ notify-send not found")
            print("    Install with: sudo apt install libnotify-bin")
    elif system == "Darwin":
        print("    Checking for terminal-notifier...")
        result = os.system("which terminal-notifier > /dev/null 2>&1")
        if result == 0:
            print("    ✓ terminal-notifier found")
        else:
            print("    ⚠ terminal-notifier not found (optional)")
            print("    Install with: brew install terminal-notifier")
except Exception as e:
    print(f"    ⚠ Cannot check backend: {e}")

# Test 6: Try sending a test notification
print("\n[6] Attempting to send test notification...")
try:
    notification.notify(
        title='LMS Test Notification',
        message='If you see this popup, OS notifications are working!',
        app_name='LMS Diagnostic',
        timeout=10
    )
    print("    ✓ Notification call completed")
    print("    → Check your system for a notification popup")
    print("    → If you don't see it, notifications may not be supported")
except Exception as e:
    print(f"    ✗ Failed to send notification: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

if system == "Linux" and not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
    print("❌ OS notifications will NOT work")
    print("Reason: No graphical display environment detected")
    print("\nThis is likely a:")
    print("  - Headless server")
    print("  - Docker container")
    print("  - SSH session without X forwarding")
    print("\nSolutions:")
    print("  1. Run the app on a machine with a desktop environment")
    print("  2. Use SSH with X forwarding: ssh -X user@host")
    print("  3. Implement email notifications instead")
    print("  4. Use webhook/API notifications")
else:
    print("✓ Environment appears capable of showing notifications")
    print("\nIf you didn't see a popup:")
    print("  1. Check system notification settings")
    print("  2. Check if notifications are blocked for Python")
    print("  3. Try running as a regular user (not root)")
    print("  4. Check notification center/action center")

print("\nIn-app notifications will always work regardless of OS notifications")
print("=" * 60)