# Complete Org Mode Conversion Summary

## Overview

This document explains the complete conversion of your vanilla Emacs org-mode configuration to Doom Emacs, including ALL components from the original configuration.

---

## Packages Required in packages.el

These packages are NOT provided by Doom's org module and must be added manually:

```elisp
;;; ~/.doom.d/packages.el

(package! org-edna)          ; Task dependencies (required by org-gtd)
(package! org-gtd)           ; GTD workflow system
(package! org-remark)        ; Text highlighting
(package! org-roam-ui)       ; Graph visualization for org-roam
(package! consult-org-roam)  ; Faster org-roam searches
```

---

## What Doom Provides vs. What You Need to Add

### ✅ Provided by Doom Org Module

When you enable these flags in `init.el`:

```elisp
(org
  +dragndrop    ; Provides org-download
  +gnuplot      ; Provides gnuplot support
  +noter        ; Provides org-noter
  +pandoc       ; Provides pandoc integration
  +pomodoro     ; Provides org-pomodoro
  +roam2)       ; Provides org-roam v2
```

Doom automatically loads and configures:
- `org-download` - Image drag-and-drop
- `org-noter` - PDF note-taking
- `org-pomodoro` - Pomodoro timer
- `org-roam` (v2) - Zettelkasten system
- Pandoc export support
- Gnuplot integration
- Basic org-mode optimizations

### ❌ NOT Provided by Doom (Must Add)

These packages are NOT included in any Doom org module flag:
- `org-gtd` - Complete GTD workflow system
- `org-edna` - Task dependencies (required by org-gtd)
- `org-roam-ui` - Graph visualization
- `consult-org-roam` - Fast searching
- `org-remark` - Text highlighting

---

## Complete Feature Matrix

| Feature | Vanilla Config | Doom Default | Conversion Status |
|---------|---------------|--------------|-------------------|
| **Directory auto-creation** | ✓ Custom | ✗ Not provided | ✅ Kept completely |
| **Essential file templates** | ✓ Custom | ✗ Not provided | ✅ Kept completely |
| **Font faces for headings** | ✓ Custom | ✗ Not provided | ✅ Kept completely |
| **TODO keywords (3 sequences)** | ✓ Custom | ✗ Different default | ✅ Kept completely |
| **Custom tags** | ✓ Custom | ✗ Different default | ✅ Kept completely |
| **Custom priorities** | ✓ Custom | ✗ Different default | ✅ Kept completely |
| **Agenda time grid** | ✓ Custom | ✗ Different default | ✅ Kept completely |
| **Custom agenda views** | ✓ Custom | ✗ Not provided | ✅ Kept completely |
| **Refile settings** | ✓ Custom | ✗ Different default | ✅ Kept completely |
| **org-tempo** | ✓ Configured | ✗ Not enabled | ✅ Fully configured |
| **Transient template menu** | ✓ Custom | ✗ Not provided | ✅ Kept completely |
| **Babel languages** | ✓ Custom list | ✗ Minimal default | ✅ Kept completely |
| **org-gtd** | ✓ Configured | ✗ Not provided | ✅ Fully configured |
| **org-edna** | ✓ Configured | ✗ Not provided | ✅ Fully configured |
| **org-roam templates** | ✓ Custom | ✗ Basic default | ✅ All 4 templates kept |
| **org-roam-ui** | ✓ Configured | ✗ Not provided | ✅ Fully configured |
| **consult-org-roam** | ✓ Configured | ✗ Not provided | ✅ Fully configured |
| **GTD↔Zettel bridges** | ✓ Custom | ✗ Not provided | ✅ All 4 functions kept |
| **Capture dispatcher** | ✓ Custom | ✗ Not provided | ✅ Kept completely |
| **Capture templates** | ✓ Custom (5) | ✗ Basic default | ✅ All 5 kept |
| **Org habit** | ✓ Custom glyphs | ✗ Default | ✅ Custom glyphs kept |
| **Org download** | ✓ Custom (Wayland) | ✓ Basic | ✅ Custom kept |
| **Org remark** | ✓ Configured | ✗ Not provided | ✅ Fully configured |
| **Src buffer naming** | ✓ Custom | ✗ Default | ✅ Custom kept |
| **Custom keybindings** | ✓ Many | ✗ Doom defaults | ✅ All migrated to map! |

---

## Syntax Changes Summary

### 1. Package Loading

**Before (Vanilla)**:
```elisp
(use-package org
  :defer t
  :ensure nil
  :commands (org-mode org-agenda)
  :config
  (setq org-todo-keywords ...))
```

**After (Doom)**:
```elisp
(after! org
  (setq org-todo-keywords ...))
```

**Why**: Doom handles lazy loading automatically.

### 2. Hooks

**Before**:
```elisp
(add-hook 'org-mode-hook #'auto-fill-mode)
(add-hook 'org-mode-hook (lambda () (setq-local yas-parents '(latex-mode))))
```

**After**:
```elisp
(add-hook! 'org-mode-hook
  #'auto-fill-mode
  (lambda () (setq-local yas-parents '(latex-mode))))
```

**Why**: Doom's `add-hook!` macro is cleaner and supports multiple functions.

### 3. Keybindings

**Before**:
```elisp
(global-set-key (kbd "C-c n g") #'ar/gtd-to-zettel)
```

**After**:
```elisp
(map! :leader
      (:prefix ("n" . "notes")
       :desc "GTD to Zettel" "g" #'ar/gtd-to-zettel))
```

**Why**: Doom's `map!` integrates with leader key system and which-key.

### 4. Org Variables

**Before**:
```elisp
(use-package org
  :custom
  (org-directory "~/org/")
  (org-todo-keywords ...))
```

**After**:
```elisp
;; CRITICAL: Before org loads
(setq org-directory (file-truename (expand-file-name "~/org/")))

(after! org
  (setq org-todo-keywords ...))
```

**Why**: `org-directory` must be set BEFORE org loads in Doom.

### 5. External Packages

**Before**:
```elisp
(use-package org-gtd
  :defer t
  :after org
  ...)
```

**After**:
```elisp
(use-package! org-gtd
  :after (org org-edna)
  ...)
```

**Why**: Doom requires `use-package!` (with !) for external packages.

---

## Critical Configuration Points

### 1. org-directory Must Be Set Early

```elisp
;; At top of config.el, BEFORE any (after! org ...)
(setq org-directory (file-truename (expand-file-name "~/org/")))
```

This is NON-NEGOTIABLE. Doom needs this set before org-mode loads.

### 2. Org-roam +roam2 Flag

```elisp
;; In init.el
(org +roam2)  ; ← Use +roam2, NOT +roam
```

`+roam` is org-roam v1 (deprecated, EOL).
`+roam2` is org-roam v2 (current, actively maintained).

### 3. Org-GTD Dependencies

org-gtd REQUIRES org-edna. Must install both:

```elisp
;; In packages.el
(package! org-edna)  ; ← Required first
(package! org-gtd)   ; ← Depends on org-edna
```

### 4. Transient Menu Structure

The transient template menu uses this structure:

```elisp
(transient-define-prefix ar/org-template-transient ()
  "Org Mode Structure Templates"
  ["" :description ar/org-transient-title  ; ← Note the structure
   ["Column 1" ...]
   ["Column 2" ...]
   ["Column 3" ...]])
```

The `""` and `:description` pattern is critical for proper display.

### 5. Org-tempo Integration

```elisp
(use-package! org-tempo
  :after org
  :config
  (add-to-list 'org-structure-template-alist '("sh" . "src shell")))
```

Doom doesn't enable org-tempo by default, so must be explicitly configured.

---

## What Changed from Original

### Removed (Redundant with Doom)

1. **`use-package` wrapper for org** - Doom loads org automatically
2. **`:ensure nil`** - Not needed in Doom
3. **`:defer t`** - Doom uses lazy loading by default
4. **`:commands`** - Doom handles autoloading
5. **Some performance settings** - Doom optimizes these already

### Modified (Adapted for Doom)

1. **Hooks** - Changed to `add-hook!`
2. **Keybindings** - Changed to `map!`
3. **Package loading** - Wrapped in `after!` or `use-package!`
4. **org-directory** - Moved to top level, before org loads
5. **Font settings** - Adapted to use `doom-font-face`

### Added (New Doom Features)

1. **Doom keybinding integration** - Leader keys, which-key descriptions
2. **Performance delays** - org-roam and org-gtd delayed with idle timers
3. **Error handling** - Better package load order

---

## Configuration File Structure

```
~/.doom.d/
├── init.el          # Module selection (you already have this)
├── packages.el      # Package declarations (ADD packages here)
└── config.el        # Your configuration (or config.org if literate)
```

### Recommended Setup

1. **Keep init.el minimal** - Just module selection
2. **Add packages to packages.el** - All `(package! ...)` declarations
3. **Put config in config.org** - Literate programming with org
4. **Tangle to config.el** - Doom does this automatically

---

## Testing Strategy

### Phase 1: Basic Installation
- Verify packages installed
- Check directories created
- Confirm files have templates

### Phase 2: Core Features
- org-tempo works
- Babel executes code
- Agenda views display

### Phase 3: GTD System
- org-gtd commands work
- org-edna loaded
- GTD keywords cycle

### Phase 4: Zettelkasten
- org-roam database syncs
- All templates work
- Links and backlinks function

### Phase 5: Extensions
- org-roam-ui displays graph
- consult-org-roam searches work
- org-remark highlights text

### Phase 6: Integration
- GTD ↔ Zettel bridges work
- Capture dispatcher functions
- Full workflows operate smoothly

**See `ORG_TESTING_GUIDE_COMPLETE.md` for detailed test procedures.**

---

## Common Issues & Solutions

### Issue: "org-gtd-capture not found"

**Cause**: org-gtd not installed.
**Fix**:
```elisp
;; Add to packages.el
(package! org-edna)
(package! org-gtd)
;; Then run
doom sync
```

### Issue: "org-roam-db-sync error"

**Cause**: Database file missing or corrupted.
**Fix**:
```bash
rm ~/.doom.d/.local/cache/org-roam.db
# In Emacs:
M-x org-roam-db-sync
```

### Issue: Transient menu doesn't appear

**Cause**: Binding not set or transient not loaded.
**Fix**: Check that `(after! (org transient) ...)` wrapper is present.

### Issue: "Cannot find org-directory"

**Cause**: org-directory set too late.
**Fix**: Move `(setq org-directory ...)` to very top of config.el.

### Issue: Templates not expanding

**Cause**: org-tempo not loaded.
**Fix**:
```elisp
(use-package! org-tempo
  :after org
  :config
  ...)
```

---

## Performance Considerations

### Startup Optimization

The configuration uses delayed loading:

```elisp
;; org-roam database sync delayed 10 seconds
(add-hook! 'after-init-hook
  (run-with-idle-timer 10 nil #'org-roam-db-autosync-enable))

;; org-gtd mode delayed 5 seconds
(run-with-idle-timer 5 nil
  (lambda ()
    (when (and (featurep 'org-gtd)
               (not (bound-and-true-p org-gtd-mode)))
      (org-gtd-mode 1))))
```

This prevents slow startup while still enabling features.

### Agenda Performance

```elisp
org-agenda-inhibit-startup t
org-agenda-dim-blocked-tasks nil
org-agenda-use-tag-inheritance nil
org-agenda-ignore-properties '(effort appt category)
```

These settings make agenda generation faster.

### File Performance

```elisp
org-element-use-cache t
org-element-cache-persistent t
org-highlight-latex-and-related nil  ; Disable heavy fontification
```

Enables caching and disables expensive features.

---

## Maintenance Tips

### Keeping Up to Date

```bash
# Update Doom and packages
doom upgrade

# Sync after config changes
doom sync

# Clean compiled files
doom clean

# Recompile
doom compile

# Check for issues
doom doctor
```

### Debugging

```elisp
;; Enable debug mode
M-x toggle-debug-on-error

;; Check package status
M-x describe-package RET org-gtd RET

;; Verify variable values
M-x describe-variable RET org-directory RET

;; Check loaded features
M-x describe-variable RET features RET
```

---

## Migration from Org-roam v1 to v2

If you have existing org-roam v1 files:

1. **Backup everything** first!
2. Change `+roam` to `+roam2` in `init.el`
3. Run `doom sync`
4. Run `M-x org-roam-migrate-wizard`
5. Verify data integrity
6. Report issues if migration fails

---

## Summary of Benefits

### From Vanilla Emacs

- ✅ All custom features preserved
- ✅ Better performance with lazy loading
- ✅ Cleaner, more maintainable code
- ✅ Integration with Doom ecosystem
- ✅ Better keybinding discoverability (which-key)

### What You Gain

- 🚀 Faster startup
- 📦 Better package management
- 🎨 Consistent UI/UX
- 🔧 Easier maintenance
- 📚 Access to Doom community

### What You Keep

- ✅ Exact same workflows
- ✅ Same keyboard shortcuts (via map!)
- ✅ All custom functions
- ✅ Same file organization
- ✅ Full GTD + Zettelkasten system

---

## Final Checklist

Before going live with this config:

- [ ] Backed up old configuration
- [ ] Added all 5 packages to `packages.el`
- [ ] Set org flags in `init.el` (including +roam2)
- [ ] Set `org-directory` at top of config
- [ ] Ran `doom sync`
- [ ] Ran `doom doctor` (no errors)
- [ ] Tested org-tempo (`<s TAB`)
- [ ] Tested transient menu (`<` in org file)
- [ ] Verified org-gtd installed
- [ ] Verified org-roam database syncs
- [ ] Tested all 4 capture templates
- [ ] Tested all agenda views
- [ ] Tested GTD ↔ Zettel bridges
- [ ] Ran complete test suite
- [ ] No errors in `*Messages*` buffer

**If all checked**: You're ready to use your new Doom Emacs org-mode setup! 🎊

---

## Support & Resources

- **Doom Emacs Docs**: https://docs.doomemacs.org/
- **Doom Discord**: https://discord.gg/qvGgnVx
- **Org-mode Manual**: https://orgmode.org/manual/
- **Org-roam Manual**: https://www.orgroam.com/manual.html
- **Org-GTD Manual**: https://github.com/Trevoke/org-gtd.el

---

**Configuration Date**: 2026-01-19  
**Doom Emacs Version**: Latest (as of 2026)  
**Org-mode Version**: Latest stable  
**Converted by**: Automated analysis with manual verification

Enjoy your powerful, complete Doom Emacs org-mode configuration!
