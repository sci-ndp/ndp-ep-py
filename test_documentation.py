#!/usr/bin/env python3
"""
Script to debug Read the Docs build issues.
"""

import os
import sys
from pathlib import Path

def check_rtd_setup():
    """Check RTD setup and identify potential issues."""
    
    print("🔍 Read the Docs Setup Checker")
    print("=" * 50)
    
    issues = []
    
    # Check .readthedocs.yaml
    rtd_config = Path(".readthedocs.yaml")
    if rtd_config.exists():
        print("✅ .readthedocs.yaml exists")
        with open(rtd_config) as f:
            content = f.read()
            if "docs/requirements.txt" in content:
                print("✅ Points to docs/requirements.txt")
            else:
                issues.append("❌ .readthedocs.yaml doesn't reference docs/requirements.txt")
    else:
        issues.append("❌ .readthedocs.yaml missing")
    
    # Check docs structure
    docs_dir = Path("docs")
    if docs_dir.exists():
        print("✅ docs/ directory exists")
        
        source_dir = docs_dir / "source"
        if source_dir.exists():
            print("✅ docs/source/ directory exists")
            
            conf_py = source_dir / "conf.py"
            if conf_py.exists():
                print("✅ docs/source/conf.py exists")
            else:
                issues.append("❌ docs/source/conf.py missing")
                
            index_rst = source_dir / "index.rst"
            if index_rst.exists():
                print("✅ docs/source/index.rst exists")
            else:
                issues.append("❌ docs/source/index.rst missing")
        else:
            issues.append("❌ docs/source/ directory missing")
    else:
        issues.append("❌ docs/ directory missing")
    
    # Check docs requirements
    docs_req = Path("docs/requirements.txt")
    if docs_req.exists():
        print("✅ docs/requirements.txt exists")
        with open(docs_req) as f:
            content = f.read()
            if "sphinx" in content.lower():
                print("✅ Contains sphinx dependency")
            else:
                issues.append("❌ docs/requirements.txt missing sphinx")
    else:
        issues.append("❌ docs/requirements.txt missing")
    
    # Check main package
    if Path("pyproject.toml").exists():
        print("✅ pyproject.toml exists")
    elif Path("setup.py").exists():
        print("✅ setup.py exists")
    else:
        issues.append("❌ No setup.py or pyproject.toml found")
    
    # Check if package is importable
    try:
        sys.path.insert(0, '.')
        import ndp_ep
        print(f"✅ Package importable (version: {getattr(ndp_ep, '__version__', 'unknown')})")
    except ImportError as e:
        issues.append(f"❌ Package not importable: {e}")
    
    # Summary
    print(f"\n📊 Summary:")
    if issues:
        print(f"❌ Found {len(issues)} issues:")
        for issue in issues:
            print(f"   {issue}")
        print(f"\n🔧 Next steps:")
        print(f"   1. Fix the issues above")
        print(f"   2. Commit and push changes")
        print(f"   3. Trigger RTD rebuild")
    else:
        print("✅ All checks passed!")
        print("🤔 If RTD still fails, check the build logs at:")
        print("   https://readthedocs.org/projects/ndp-ep/builds/")
    
    return len(issues) == 0

def simulate_rtd_build():
    """Simulate RTD build process locally."""
    
    print("\n🔄 Simulating RTD Build Process")
    print("=" * 50)
    
    try:
        # Change to docs directory
        os.chdir("docs")
        
        # Try to build
        print("📦 Installing requirements...")
        os.system("pip install -r requirements.txt")
        
        print("🏗️  Building documentation...")
        result = os.system("sphinx-build -M html source build -v")
        
        if result == 0:
            print("✅ Local build successful!")
            print("🎯 RTD should work if all dependencies are correct")
        else:
            print("❌ Local build failed")
            print("🔧 Fix local build first, then RTD should work")
            
    except Exception as e:
        print(f"❌ Simulation failed: {e}")

if __name__ == "__main__":
    print("Running RTD diagnostics...\n")
    
    setup_ok = check_rtd_setup()
    
    if setup_ok:
        simulate = input("\n🤔 Run local build simulation? (y/N): ")
        if simulate.lower() == 'y':
            simulate_rtd_build()
    
    print(f"\n💡 If issues persist:")
    print(f"   - Check RTD build logs: https://readthedocs.org/projects/your-project/builds/")
    print(f"   - Ensure all files are committed and pushed")
    print(f"   - Try manually triggering a rebuild in RTD dashboard")