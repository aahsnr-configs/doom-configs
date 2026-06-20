# Prettify Symbols Testing Guide for Doom Emacs

This guide will help you test the prettify symbols configuration for all supported modes.

## Installation

1. **Add configuration to your Doom Emacs config.org**:
   - Copy the contents of `tmp.org` into your `~/.doom.d/config.org` file
   - Or tangle it to a separate file and load it from your config

2. **Sync Doom Emacs**:
   ```bash
   doom sync
   ```

3. **Restart Emacs** (or run `M-x doom/reload` which is bound to `SPC h r r`)

## Quick Access

The prettify symbols transient menu is available at: **`SPC c s`**

From this menu you can:
- **s**: Toggle prettify-symbols-mode on/off
- **a**: Toggle aggressive mode (prettifies in strings/comments)
- **u**: Cycle unprettify-at-point behavior
- **p**: Show symbol at point (reveals actual text)
- **l**: List all symbols for current mode
- **d**: Describe character at point
- **r**: Reload prettify mode
- **i**: Insert Unicode character

---

## Testing by Mode

### 1. Emacs Lisp Mode Testing

**Create test file**: `test-elisp.el`

```elisp
;; Test basic symbols
(defun test-function ()
  "Test function with various symbols."
  (let ((x 5)
        (y 10))
    (if (>= x y)
        (message "x is greater than or equal to y")
      (when (!= x y)
        (message "x is not equal to y")))
    ;; Arrow test
    (message "arrow test -> => <-")
    (message "ellipsis test...")
    ;; Lambda test
    (lambda (x) (* x 2))
    ;; Logical operators
    (and (not nil) (or t nil))
    ;; Comparison
    (when (/= 1 2)
      (message "not equal"))))

(defmacro test-macro (x)
  "Test macro definition."
  `(* ,x 2))
```

**What to verify**:
- ✓ `defun` should appear as `ƒ`
- ✓ `defmacro` should appear as `μ`
- ✓ `lambda` should appear as `λ`
- ✓ `>=` should appear as `≥`
- ✓ `!=` should appear as `≠`
- ✓ `->` should appear as `→`
- ✓ `=>` should appear as `⇒`
- ✓ `<-` should appear as `←`
- ✓ `...` should appear as `…`
- ✓ `not` should appear as `¬`
- ✓ `and` should appear as `∧`
- ✓ `or` should appear as `∨`
- ✓ `/=` should appear as `≠`

**Test interactivity**:
1. Open the file in Emacs
2. Move cursor over prettified symbols - they should reveal when cursor approaches (right-edge behavior)
3. Press `SPC c s` then `p` when on a symbol to see the actual text
4. Press `SPC c s` then `l` to see all available symbols for this mode

---

### 2. Python Mode Testing

**Create test file**: `test-python.py`

```python
# Test Python-specific symbols
def calculate_sum(numbers):
    """Calculate sum with type hints."""
    total: int = 0
    pi_value: float = 3.14159
    name: str = "Python"
    is_valid: bool = True
    
    # Test operators
    if total >= 0 and name != "":
        for num in numbers:
            if num not in [0, 1]:
                total = total + num
    
    # Test None, True, False
    result = None
    if total > 0:
        result = True
    else:
        result = False
    
    # Test arrows and return
    data -> int
    return total

class Calculator:
    """Test class definition."""
    
    def __init__(self):
        self.value = 0
    
    def yield_values(self):
        """Test yield."""
        for i in range(10):
            yield i

# More operator tests
if x <= y or x == y:
    print("less than or equal, or equal")

# Ellipsis test
print("More text...")

# Lambda in Python
square = lambda x: x ** 2
```

**What to verify**:
- ✓ `def` should appear as `ƒ`
- ✓ `class` should appear as `𝒞`
- ✓ `return` should appear as `⟼`
- ✓ `yield` should appear as `⟻`
- ✓ `not` should appear as `¬`
- ✓ `in` should appear as `∈`
- ✓ `not in` should appear as `∉`
- ✓ `and` should appear as `∧`
- ✓ `or` should appear as `∨`
- ✓ `None` should appear as `∅`
- ✓ `True` should appear as `⊤`
- ✓ `False` should appear as `⊥`
- ✓ `int` should appear as `ℤ`
- ✓ `float` should appear as `ℝ`
- ✓ `str` should appear as `𝕊`
- ✓ `bool` should appear as `𝔹`
- ✓ `lambda` should appear as `λ`
- ✓ All base symbols (arrows, >=, <=, !=, ==, ...) should work

**Test aggressive mode**:
1. Press `SPC c s` then `a` to enable aggressive mode
2. Strings and comments should now also be prettified
3. Press `a` again to toggle back to default mode

---

### 3. Shell/Bash Mode Testing

**Create test file**: `test-script.sh`

```bash
#!/bin/bash

# Test shell operators
x=5
y=10

# Test comparison operators
if [ $x -eq 5 ]; then
    echo "x equals 5"
fi

if [ $x -ne $y ]; then
    echo "x is not equal to y"
fi

if [ $x -le $y ]; then
    echo "x is less than or equal to y"
fi

if [ $x -ge 0 ]; then
    echo "x is greater than or equal to 0"
fi

# Test logical operators
if [ $x -gt 0 ] && [ $y -gt 0 ]; then
    echo "both positive"
fi

if [ $x -lt 0 ] || [ $y -gt 0 ]; then
    echo "at least one condition is true"
fi

# Test arrows and ellipsis
echo "Processing -> completed"
echo "Waiting..."

# Test other base symbols
if [ "$result" != "error" ]; then
    echo "Success => $result"
fi
```

**What to verify**:
- ✓ `-eq` should appear as `=`
- ✓ `-ne` should appear as `≠`
- ✓ `-le` should appear as `≤`
- ✓ `-ge` should appear as `≥`
- ✓ `&&` should appear as `∧`
- ✓ `||` should appear as `∨`
- ✓ All base symbols should work

---

### 4. Org Mode Testing

**Create test file**: `test-org.org`

```org
* Test Org Mode Prettify Symbols

** Arrows and comparisons
- Process flow: start -> middle -> end
- Implication: condition => result
- Reverse flow: end <- middle <- start
- Greater or equal: x >= 5
- Less or equal: x <= 10
- Not equal: x != y

** Ellipsis test
More content...

** Source blocks
#+BEGIN_SRC python
def example():
    return True
#+END_SRC

#+begin_src elisp
(defun example ()
  (message "test"))
#+end_src
```

**What to verify**:
- ✓ `->` should appear as `→`
- ✓ `<-` should appear as `←`
- ✓ `=>` should appear as `⇒`
- ✓ `<=` should appear as `≤`
- ✓ `>=` should appear as `≥`
- ✓ `!=` should appear as `≠`
- ✓ `...` should appear as `…`
- ✓ `#+BEGIN_SRC` should appear as `»` (if uncommented)
- ✓ `#+END_SRC` should appear as `«` (if uncommented)

**Note**: If you're using `org-modern`, you may want to keep the source block markers commented out to avoid conflicts.

---

### 5. Markdown Mode Testing

**Create test file**: `test-markdown.md`

```markdown
# Test Markdown Prettify Symbols

## Arrows and comparisons
- Process: start -> end
- Implication: condition => result
- Reverse: end <- start
- x >= 5
- y <= 10
- a != b

## Ellipsis
More content...

## Code blocks
```python
def example():
    return True
```

## Task lists
- [ ] Unchecked task
- [x] Checked task
- [X] Another checked task
```

**What to verify**:
- ✓ `->` should appear as `→`
- ✓ `<-` should appear as `←`
- ✓ `=>` should appear as `⇒`
- ✓ `<=` should appear as `≤`
- ✓ `>=` should appear as `≥`
- ✓ `!=` should appear as `≠`
- ✓ `...` should appear as `…`
- ✓ ` ``` ` should appear as `‣`
- ✓ `[ ]` should appear as `☐`
- ✓ `[x]` should appear as `☑`
- ✓ `[X]` should appear as `☑`

---

## Common Testing Procedures

### A. Test Cursor Unprettification

1. Open any test file
2. Move cursor over a prettified symbol
3. **Expected behavior**: Symbol should reveal when cursor approaches from the right
4. Press `SPC c s` then `u` to cycle through unprettify modes:
   - `nil`: No unprettification (symbol always pretty)
   - `right-edge`: Unprettifies when cursor at right edge (default)
   - `t`: Unprettifies when cursor is anywhere on the symbol

### B. Test List All Symbols

1. Open any test file
2. Press `SPC c s` then `l`
3. **Expected**: A buffer showing all available symbols for that mode

### C. Test Symbol at Point

1. Move cursor to a prettified symbol
2. Press `SPC c s` then `p`
3. **Expected**: Echo area shows the actual text (e.g., "Symbol: \"def\"")

### D. Test Mode Toggle

1. Press `SPC c s` then `s`
2. **Expected**: Prettify mode turns off (symbols show as text)
3. Press `s` again to turn it back on

### E. Test Reload

1. Modify the configuration (e.g., add a new symbol)
2. Re-evaluate the configuration
3. Press `SPC c s` then `r`
4. **Expected**: Symbols update immediately without restarting Emacs

---

## Troubleshooting

### Symbols don't appear prettified

1. **Check if mode is enabled**:
   - `M-x describe-variable RET prettify-symbols-mode RET`
   - Should show `t` (enabled)

2. **Check if global mode is enabled**:
   - `M-x describe-variable RET global-prettify-symbols-mode RET`
   - Should show `t`

3. **Verify alist is set**:
   - `M-x describe-variable RET prettify-symbols-alist RET`
   - Should show a list of symbol mappings

4. **Check font support**:
   - Some symbols require Unicode font support
   - Test: `M-x insert-char RET 2192 RET` (should insert →)

### Keybinding doesn't work (SPC c s)

1. **Check if transient is loaded**:
   - `M-x ar/prettify-symbols-transient RET`
   - Should open the menu

2. **Verify keybinding**:
   - `SPC h k` then `SPC c s`
   - Should show: `ar/prettify-symbols-transient`

3. **Check for conflicts**:
   - `M-x describe-key RET SPC c s`
   - If it shows something else, there's a keybinding conflict

### Hooks not firing

1. **Check hook list**:
   - For Python: `M-x describe-variable RET python-mode-hook RET`
   - Should include `ar/prettify-symbols-python-setup`

2. **Test manually**:
   - Open a Python file
   - `M-x ar/prettify-symbols-python-setup RET`
   - Symbols should now appear

---

## Performance Testing

### Check startup impact

```elisp
;; Add to your config temporarily to measure impact
(defun measure-prettify-load-time ()
  (let ((start-time (current-time)))
    (load "your-prettify-config.el")
    (message "Prettify config loaded in: %f seconds"
             (float-time (time-subtract (current-time) start-time)))))
```

**Expected**: Load time should be negligible (< 0.01 seconds)

---

## Advanced Testing

### Test with large files

1. Create a large Python file (1000+ lines)
2. Open it and observe:
   - Initial rendering time
   - Scrolling performance
   - Editing responsiveness

**Expected**: No noticeable performance degradation

### Test save behavior

1. Edit a file with prettified symbols
2. Save the file (`SPC f s` or `C-x C-s`)
3. **Expected**: No indentation or formatting issues

If you encounter save issues, uncomment the save protection hooks in the configuration.

---

## Cleanup

To remove or disable the configuration:

1. **Temporarily disable**:
   ```elisp
   M-x global-prettify-symbols-mode RET
   ```

2. **Permanently remove**:
   - Remove the configuration from your `config.org`
   - Run `doom sync`
   - Restart Emacs

---

## Summary Checklist

- [ ] Keybinding `SPC c s` works
- [ ] Transient menu appears and all options work
- [ ] Emacs Lisp symbols prettify correctly
- [ ] Python symbols prettify correctly
- [ ] Shell/Bash symbols prettify correctly
- [ ] Org mode symbols prettify correctly
- [ ] Markdown symbols prettify correctly
- [ ] Cursor unprettification works as expected
- [ ] Aggressive mode toggle works
- [ ] List symbols function works
- [ ] Show symbol at point works
- [ ] No performance issues
- [ ] No save/indentation issues

If all items are checked, your configuration is working perfectly!
