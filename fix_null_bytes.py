import os
import sys
import re

def fix_file(filepath):
    try:
        # Read the file in binary mode
        with open(filepath, 'rb') as f:
            content = f.read()
        
        # Check if it contains null bytes
        if b'\x00' in content:
            print(f"Fixing null bytes in {filepath}")
            # Remove null bytes
            content = content.replace(b'\x00', b'')
            
            # Write back to file
            with open(filepath, 'wb') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def scan_directory(directory):
    fixed_files = 0
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if fix_file(filepath):
                    fixed_files += 1
    
    return fixed_files

def main():
    directory = '.'  # Current directory
    fixed_files = scan_directory(directory)
    print(f"Fixed {fixed_files} files with null bytes")

if __name__ == "__main__":
    main() 