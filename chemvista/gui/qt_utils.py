"""Qt utility functions for ChemVista GUI"""
import os
import glob
import platform
import sys


def print_system_info(env_changes=None):
    """Print system information for debugging graphics and Qt issues"""
    print("=" * 60)
    print("ChemVista System Environment Information")
    print("=" * 60)
    
    # System info
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Machine: {platform.machine()}")
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    
    # Display and graphics info
    display = os.environ.get('DISPLAY', 'Not set')
    print(f"Display: {display}")
    
    # Check for common graphics environment variables
    graphics_vars = {
        'LIBGL_ALWAYS_SOFTWARE': 'Software OpenGL rendering',
        'GALLIUM_DRIVER': 'Gallium graphics driver',
        'MESA_GL_VERSION_OVERRIDE': 'Mesa OpenGL version override',
        'VTK_USE_LEGACY_RENDERING': 'VTK legacy rendering mode',
        'VTK_USE_LEGACY_DEPTH_PEELING': 'VTK legacy depth peeling'
    }
    
    print("\nGraphics Environment:")
    for var, description in graphics_vars.items():
        value = os.environ.get(var, 'Not set')
        status = ""
        if env_changes and var in env_changes:
            if env_changes[var]['changed']:
                old_val = env_changes[var]['old']
                status = f" [CHANGED from '{old_val}']"
        print(f"  {var}: {value}{status}")
    
    # Qt environment variables
    qt_vars = {
        'QT_QPA_PLATFORM': 'Qt platform abstraction',
        'QT_X11_NO_MITSHM': 'Qt X11 shared memory disabled',
        'QT_LOGGING_RULES': 'Qt logging configuration'
    }
    
    print("\nQt Environment:")
    for var, description in qt_vars.items():
        value = os.environ.get(var, 'Not set')
        status = ""
        if env_changes and var in env_changes:
            if env_changes[var]['changed']:
                old_val = env_changes[var]['old']
                status = f" [CHANGED from '{old_val}']"
        print(f"  {var}: {value}{status}")
    
    # OpenGL detection
    opengl_supported = detect_opengl_support()
    print(f"\nOpenGL Support: {'✓ Detected' if opengl_supported else '✗ Not detected or insufficient'}")
    
    # Check for glxinfo output if available
    try:
        import subprocess
        result = subprocess.run(['glxinfo', '-B'], capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'OpenGL vendor' in line or 'OpenGL renderer' in line or 'OpenGL version' in line:
                    print(f"  {line.strip()}")
    except:
        print("  glxinfo not available - install mesa-utils for detailed OpenGL info")
    
    if env_changes:
        changed_vars = [var for var, info in env_changes.items() if info['changed']]
        if changed_vars:
            print(f"\nEnvironment variables modified by ChemVista: {', '.join(changed_vars)}")
        else:
            print("\nNo environment variables were modified (all were already set)")
    
    print("=" * 60)


def setup_qt_environment():
    """Setup Qt environment variables to prevent common X11 and threading issues"""
    changes = {}
    
    # Set Qt platform to xcb (X11) explicitly
    var = 'QT_QPA_PLATFORM'
    old_val = os.environ.get(var)
    if var not in os.environ:
        os.environ[var] = 'xcb'
        changes[var] = {'old': 'Not set', 'new': 'xcb', 'changed': True}
    else:
        changes[var] = {'old': old_val, 'new': old_val, 'changed': False}
    
    # Disable MIT-SHM to prevent X11 issues
    var = 'QT_X11_NO_MITSHM'
    old_val = os.environ.get(var)
    if var not in os.environ:
        os.environ[var] = '1'
        changes[var] = {'old': 'Not set', 'new': '1', 'changed': True}
    else:
        changes[var] = {'old': old_val, 'new': old_val, 'changed': False}
    
    return changes


def setup_opengl_environment():
    """Setup OpenGL environment variables to handle graphics compatibility issues"""
    changes = {}
    
    # Force software rendering as fallback for systems with poor OpenGL support
    var = 'LIBGL_ALWAYS_SOFTWARE'
    old_val = os.environ.get(var)
    if var not in os.environ:
        # Only set this if we detect potential OpenGL issues
        # You can make this conditional based on system detection
        pass  # Uncomment next line if needed: os.environ[var] = '1'
        changes[var] = {'old': 'Not set', 'new': 'Not set', 'changed': False}
    else:
        changes[var] = {'old': old_val, 'new': old_val, 'changed': False}
    
    # Disable VTK multisampling which can cause shader issues
    var = 'VTK_USE_LEGACY_DEPTH_PEELING'
    old_val = os.environ.get(var)
    if var not in os.environ:
        os.environ[var] = '1'
        changes[var] = {'old': 'Not set', 'new': '1', 'changed': True}
    else:
        changes[var] = {'old': old_val, 'new': old_val, 'changed': False}
    
    # Set VTK to use older, more compatible OpenGL features
    var = 'VTK_USE_LEGACY_RENDERING'
    old_val = os.environ.get(var)
    if var not in os.environ:
        os.environ[var] = '1'
        changes[var] = {'old': 'Not set', 'new': '1', 'changed': True}
    else:
        changes[var] = {'old': old_val, 'new': old_val, 'changed': False}
    
    # Track other variables that might be relevant
    for var in ['GALLIUM_DRIVER', 'MESA_GL_VERSION_OVERRIDE']:
        old_val = os.environ.get(var)
        changes[var] = {'old': old_val or 'Not set', 'new': old_val or 'Not set', 'changed': False}
    
    return changes


def setup_environment():
    """Setup all environment variables for ChemVista"""
    # Collect changes from both setup functions
    qt_changes = setup_qt_environment()
    opengl_changes = setup_opengl_environment()
    
    # Combine changes
    all_changes = {**qt_changes, **opengl_changes}
    
    # Print system info with change tracking
    print_system_info(all_changes)


def detect_opengl_support():
    """Detect if system has proper OpenGL support"""
    try:
        import subprocess
        result = subprocess.run(['glxinfo'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            # Check for OpenGL 3.2+ support
            if 'OpenGL version string: 3.' in result.stdout or 'OpenGL version string: 4.' in result.stdout:
                return True
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass
    return False


def enable_software_rendering():
    """Force software rendering for compatibility"""
    os.environ['LIBGL_ALWAYS_SOFTWARE'] = '1'
    os.environ['GALLIUM_DRIVER'] = 'llvmpipe'
    print("Software rendering enabled for compatibility")