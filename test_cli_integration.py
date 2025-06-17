#!/usr/bin/env python3
"""
Test CLI integration with tree organization.
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, expected_in_output=None):
    """Run a command and check output."""
    print(f"🔍 Testing: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"✅ Command succeeded")
            if expected_in_output:
                if expected_in_output in result.stdout:
                    print(f"✅ Found expected text: '{expected_in_output}'")
                else:
                    print(f"⚠️  Expected text '{expected_in_output}' not found in output")
                    print(f"Output preview: {result.stdout[:200]}...")
        else:
            print(f"❌ Command failed with return code {result.returncode}")
            print(f"Error: {result.stderr}")
            
        return result
        
    except subprocess.TimeoutExpired:
        print(f"⏰ Command timed out")
        return None
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def main():
    """Test CLI integration."""
    print("🧪 Testing CLI Integration with Tree Organization")
    print("=" * 60)
    
    # Test basic commands
    tests = [
        (["python", "chatgpt_browser.py", "info"], "Total conversations"),
        (["python", "chatgpt_browser.py", "list", "5"], "conversations"),
        (["python", "chatgpt_browser.py", "search", "organizer"], "matching"),
    ]
    
    success_count = 0
    for cmd, expected in tests:
        result = run_command(cmd, expected)
        if result and result.returncode == 0:
            success_count += 1
        print("-" * 40)
    
    print(f"\n📊 Results: {success_count}/{len(tests)} tests passed")
    
    # Test tree organization persistence
    print("\n🌳 Testing tree organization persistence...")
    
    org_file = Path.home() / '.chatgpt' / 'conversations_organization.json'
    if org_file.exists():
        print(f"✅ Organization file exists: {org_file}")
        
        # Read and check structure
        import json
        with open(org_file) as f:
            data = json.load(f)
            
        folders = [node for node in data['tree_nodes'].values() if node['node_type'] == 'folder']
        conversations = [node for node in data['tree_nodes'].values() if node['node_type'] == 'conversation']
        
        print(f"✅ Found {len(folders)} folders and {len(conversations)} organized conversations")
        print(f"✅ Root nodes: {len(data['root_nodes'])}")
        
        # Check for our demo folders
        folder_names = [node['name'] for node in folders]
        expected_folders = ['💼 Work Projects', '📚 Learning & Education', '🏠 Personal']
        
        for folder in expected_folders:
            if folder in folder_names:
                print(f"✅ Found expected folder: {folder}")
            else:
                print(f"❌ Missing expected folder: {folder}")
                
    else:
        print(f"❌ Organization file not found: {org_file}")
    
    print("\n🎯 Testing complete!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()