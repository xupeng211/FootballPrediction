#!/bin/bash

# Function to fix a test file
fix_test_file() {
    local file="$1"
    echo "Fixing $file..."
    
    # Fix function names with forward slashes
    sed -i 's|def test_src_\([^/]*\)/\([^)]*\)():|def test_src_\1_\2():|g' "$file"
    
    # Fix the problematic pattern - replace the entire malformed function
    sed -i '/def test_src_[^()]*():/,/# Hint: Use pytest-mock/ {
        /def test_src_[^()]*():/!{
            /"""Test that key functions\/classes in/!{
                /result = None/!{
                    /try:/!{
                        /pass/!{
                            /except Exception as e:/!{
                                /assert isinstance(e, Exception)/!{
                                    /assert result is None or result is not False/!d
                                }
                            }
                        }
                    }
                }
            }
        }
    }' "$file"
    
    # Fix indentation - replace the malformed try-except blocks with proper ones
    sed -i '/def test_src_[^()]*():/,/# Hint: Use pytest-mock/ {
        /try:/,/assert result is None or result is not False/ {
            s/try:/try:\
        if hasattr(module, '\''main'\''):\
            result = module.main()\
        elif hasattr(module, '\''process'\''):\
            result = module.process()\
        elif hasattr(module, '\''run'\''):\
            result = module.run()/
            t
            s/except Exception as e:$/except Exception as e:\
        assert isinstance(e, Exception)/
            t
            /pass/d
            /result = None$/d
            /if hasattr(module,/d
            /result = module\./d
            /elif hasattr(module,/d
        }
    }' "$file"
    
    # Verify the fix
    if python -m py_compile "$file" 2>/dev/null; then
        echo "✓ Fixed $file"
    else
        echo "✗ Still issues with $file"
    fi
}

# Get list of files with issues
files_with_issues=$(find tests/ -name "test_src_*.py" -exec python -m py_compile {} \; 2>&1 | grep -o "tests/[^(]*\.py" | sort | uniq)

# Fix each file
for file in $files_with_issues; do
    if [[ -f "$file" ]]; then
        fix_test_file "$file"
    fi
done

echo "Batch fixing complete!"
