# Complete Org Mode Testing Guide for Doom Emacs

This guide tests EVERY feature in your converted org-mode configuration.

## Pre-Installation Requirements

### Required Packages

Add to `~/.doom.d/packages.el`:

```elisp
(package! org-edna)          ; Task dependencies
(package! org-gtd)           ; GTD workflow
(package! org-remark)        ; Text highlighting
(package! org-roam-ui)       ; Graph visualization
(package! consult-org-roam)  ; Fast searches
```

### Required init.el Flags

```elisp
(org
  +dragndrop
  +gnuplot
  +noter
  +pandoc
  +pomodoro
  +roam2)   ; IMPORTANT: Use +roam2, NOT +roam
```

### Installation Steps

1. Add packages to `packages.el`
2. Update flags in `init.el`
3. Run: `doom sync`
4. Run: `doom doctor` (check for errors)
5. Restart Emacs
6. Verify: `M-x package-list-packages` should show all installed

---

## Phase 1: Directory & File Structure

### Test 1.1: Auto-Created Directories

```bash
# Verify all directories exist
ls -la ~/org/
ls -la ~/org/roam/
ls -la ~/org/roam/zettel/
ls -la ~/org/roam/literature/
ls -la ~/org/roam/ideas/
ls -la ~/org/roam/projects/
ls -la ~/org/roam/daily/
ls -la ~/org/gtd/
ls -la ~/org/reviews/
ls -la ~/org/downloads/
ls -la ~/org/noter/
ls -la ~/org/archive/
ls -la ~/org/attachments/
ls -la ~/org/backups/
```

**Expected**: All directories created automatically on first Emacs start.

### Test 1.2: Essential Files

```bash
# Check essential files
ls ~/org/*.org
cat ~/org/journal.org
cat ~/org/habits.org
cat ~/org/goals.org
cat ~/org/reading.org
cat ~/org/meetings.org
cat ~/org/roam/ideas/fleeting.org
```

**Expected**: All files exist with correct templates and tags.

---

## Phase 2: Org Tempo & Structure Templates

### Test 2.1: Standard Org Tempo

**Test**:
1. Open any org file
2. Type: `<s` then `TAB`

**Expected**: Expands to:
```org
#+begin_src 
#+end_src
```

### Test 2.2: Custom Templates

**Test each shortcut**:
- `<sh TAB` → shell source block
- `<el TAB` → emacs-lisp source block
- `<py TAB` → python source block
- `<jpy TAB` → jupyter-python block
- `<tex TAB` → latex source block

**Expected**: All expand correctly with language specified.

### Test 2.3: Transient Template Menu

**Test**:
1. Go to beginning of line in org file
2. Press: `<`
3. Should open transient menu

**Expected**: Menu appears with these columns:
- **Basic**: ascii, center, comment, example, export, html, latex, note, quote, verse
- **Head**: index, ASCII, INCLUDE, HTML, LaTeX
- **Source**: src, emacs-lisp, python, powershell, ruby, sh, golang
- **Misc**: mermaid, plantuml, ipython, Perl tangled, quit, insert <

**Test menu options**:
1. Press `s` → should insert `#+begin_src`
2. Press `e` → should insert emacs-lisp block
3. Press `y` → should insert python block
4. Press `q` → should quit menu
5. Press `<` → should insert literal `<`

### Test 2.4: Template with Region

1. Type some text: "hello world"
2. Select the text (region)
3. Press `<`
4. Select template (e.g., `c` for center)

**Expected**: Text wrapped in `#+begin_center ... #+end_center`

---

## Phase 3: Org Babel

### Test 3.1: Babel Languages Loaded

**Test**:
```elisp
M-x describe-variable RET org-babel-load-languages RET
```

**Expected**: Should show:
- emacs-lisp, perl, python, ruby, js, css, sass, C, java, shell, plantuml all set to `t`

### Test 3.2: Execute Code Blocks

**Test**:
1. Create this block:
   ```org
   #+begin_src emacs-lisp
   (+ 1 2)
   #+end_src
   ```
2. Put cursor inside block
3. Press: `SPC m '` or `C-c C-c`

**Expected**: 
- Should NOT ask for confirmation (org-confirm-babel-evaluate is nil)
- Result appears: `#+RESULTS: : 3`

### Test 3.3: Multiple Languages

**Test Python**:
```org
#+begin_src python
print("Hello from Python")
#+end_src
```

**Test Shell**:
```org
#+begin_src shell
echo "Hello from Shell"
#+end_src
```

**Execute each** with `C-c C-c`.

**Expected**: Results appear correctly for each language.

---

## Phase 4: Org GTD

### Test 4.1: Org-GTD Installation

**Verify packages**:
```elisp
M-x describe-package RET org-edna RET
M-x describe-package RET org-gtd RET
```

**Expected**: Both packages installed and loaded.

### Test 4.2: GTD Directory

```bash
ls ~/org/gtd/
```

**Expected**: Directory exists (org-gtd may create files here on first use).

### Test 4.3: GTD Capture

**Test**:
```elisp
M-x org-gtd-capture RET
```

**Expected**: Opens GTD capture interface with proper templates.

### Test 4.4: GTD Keywords

**Create test file**: `~/org/gtd/test.org`

```org
* INBOX Test inbox item
* GTD-NEXT Test next action
* GTD-WAIT Test waiting item
* GTD-DONE Completed item
```

**Test**: Cycle through states with `SPC m t`

**Expected**:
- INBOX → GTD-NEXT → GTD-WAIT → GTD-DONE → GTD-CNCL
- Each keyword has proper color from config

### Test 4.5: GTD Agenda Commands

**Test each**:
- `SPC a g` → org-gtd-engage
- `SPC a i` → org-gtd-process-inbox
- `SPC a n` → org-gtd-show-all-next
- `SPC a s` → org-gtd-show-stuck-projects

**Expected**: Commands execute without errors (may be empty if no GTD items yet).

### Test 4.6: Org-Edna Dependencies

**Test**:
```elisp
M-x describe-function RET org-edna-mode RET
```

**Expected**: Function exists, org-edna loaded.

**In org file**:
- Org-edna-mode should be active (check mode line)

---

## Phase 5: Org Roam Complete

### Test 5.1: Org-Roam Database

**Check database file**:
```bash
ls ~/.doom.d/.local/cache/org-roam.db
# or
ls ~/.emacs.d/.local/cache/org-roam.db
```

**Test**:
```elisp
M-x org-roam-db-diagnose RET
```

**Expected**: 
- Database file exists
- No errors in diagnosis

### Test 5.2: Create Zettel Note

**Test**:
1. `SPC n r f` (find-or-create)
2. Enter title: "Test Zettelkasten Note"
3. Select template: `z` (zettel)

**Expected**:
- File created in `~/org/roam/zettel/`
- Contains sections: Core Idea, Elaboration, Evidence, Connections, Source
- Has tags: `:zettel:permanent:`

### Test 5.3: Create Literature Note

1. `SPC n r f`
2. Title: "Test Literature Note"
3. Template: `l` (literature)

**Expected**:
- File in `~/org/roam/literature/`
- Has Source section with prompts for Author, Title, Year, Type, URL
- Sections: Summary, Key Takeaways, Quotes, Personal Notes, Related Ideas
- Tag: `:literature:`

### Test 5.4: Create Project Note

1. `SPC n r f`
2. Title: "Test Project Note"
3. Template: `p` (project)

**Expected**:
- File in `~/org/roam/projects/`
- Sections for Project Context, Why This Matters, Resources, etc.
- GTD Link section
- Tags: `:project:context:`

### Test 5.5: Create Fleeting Note

1. `SPC n r f`
2. Title doesn't matter (will use fleeting.org)
3. Template: `i` (fleeting)

**Expected**:
- Appends to `~/org/roam/ideas/fleeting.org`
- Entry has checklist for processing later

### Test 5.6: Daily Notes

**Test**:
- `SPC n r d d` → Today's daily note
- `SPC n r d D` → Select date

**Expected**:
- Creates file in `~/org/roam/daily/`
- Format: `YYYY-MM-DD.org`
- Title: "YYYY-MM-DD Weekday"
- Tag: `:daily:`

### Test 5.7: Note Linking

1. In any roam note
2. `SPC n r i` (insert link)
3. Search for another note or create new

**Expected**:
- Link inserted
- Backlink appears in target note

---

## Phase 6: Org-Roam UI

### Test 6.1: Launch UI

**Test**:
```elisp
SPC n r u   ; or M-x org-roam-ui-open
```

**Expected**:
- Opens browser with graph visualization
- Shows your org-roam notes as nodes
- Links between notes as edges
- Interactive: can click nodes to open files

### Test 6.2: UI Features

**In the UI**:
- Zoom in/out works
- Drag nodes works
- Click node opens file in Emacs
- Filter by tags works
- Theme matches Doom theme

---

## Phase 7: Consult Org-Roam

### Test 7.1: Fast Search

**Test**:
```elisp
SPC n r s   ; or M-x consult-org-roam-search
```

**Expected**:
- Fast grep-style search across all roam notes
- Live preview as you type
- Select result opens file

### Test 7.2: Forward Links

In any roam note:
```elisp
SPC n r l   ; or M-x consult-org-roam-forward-links
```

**Expected**: Shows all links FROM current note.

### Test 7.3: Backlinks

```elisp
SPC n r b   ; or M-x consult-org-roam-backlinks
```

**Expected**: Shows all links TO current note.

---

## Phase 8: GTD ↔ Zettelkasten Bridges

### Test 8.1: GTD to Zettelkasten

**Setup**:
1. Create: `~/org/gtd/projects.org`
2. Add: `* PROJECT Build Website`
3. Put cursor on heading

**Test**:
```elisp
SPC n g   ; or M-x ar/gtd-to-zettel
```

**Expected**:
- Creates note in `~/org/roam/projects/`
- Note titled: "Project: Build Website"
- GTD project gets backlink to zettel note
- Zettel note has link to GTD project

### Test 8.2: Zettelkasten to GTD

**Setup**:
1. Open any roam note
2. Add tasks:
   ```org
   * TODO Research framework
   * NEXT Write proposal
   ```

**Test**:
```elisp
SPC n z   ; or M-x ar/zettel-to-gtd
```

**Expected**:
- Tasks extracted to `~/org/gtd/inbox.org`
- Each task has INBOX keyword
- PROPERTIES with FROM link back to zettel
- Message: "Extracted N tasks to GTD inbox"

### Test 8.3: Fleeting Notes Access

**Test**:
```elisp
SPC o f   ; or M-x ar/fleeting-to-permanent
```

**Expected**: Opens `~/org/roam/ideas/fleeting.org`

### Test 8.4: Weekly Review

**Test**:
```elisp
SPC o w   ; or M-x ar/weekly-review
```

**Expected**:
- Creates `~/org/reviews/YYYY-WWw-review.org`
- File contains:
  - GTD Review section with actual counts
  - Zettelkasten Review section
  - Weekly Reflections
  - Weekly Metrics
- Cursor jumps to "What Went Well?" section

**Verify counts**:
1. Count actual items in inbox/next/etc.
2. Compare with counts in review file
3. Should match

---

## Phase 9: Custom Agenda Commands

### Test 9.1: Daily Dashboard

**Test**:
```elisp
SPC o A   ; then d
```

**Expected sections**:
- 📅 Today's Schedule (1 day span)
- 💻 @Computer Tasks
- 🏠 @Home Tasks
- 📥 Inbox

### Test 9.2: Weekly Review Agenda

**Test**:
```elisp
SPC o A   ; then w
```

**Expected sections**:
- 📥 GTD Inbox (Must Process)
- ⏳ Waiting For (Follow Up)
- 🚫 Stuck Projects
- ✅ All NEXT Actions

### Test 9.3: Projects Dashboard

**Test**:
```elisp
SPC o A   ; then p
```

**Expected sections**:
- 📋 GTD Projects (Execution)
- 🚀 Active Project Context

### Test 9.4: GTD Views (submenu)

**Test**:
```elisp
SPC o A   ; then g
```

**Expected**: Shows submenu with options:
- `n` → Next Actions
- `i` → Inbox (Unprocessed)
- `w` → Waiting For
- `s` → Stuck Projects
- `c` → By Context (shows @computer, @home, @errands, @phone)

**Test each sub-view** to ensure they work.

### Test 9.5: Agenda Styling

**Verify visual elements**:
- Block separator: `─` character
- Time grid with ticks at 800, 1000, 1200, etc.
- Current time indicator: `◀ now ───────`
- Tags column at position -80

---

## Phase 10: Capture Dispatcher

### Test 10.1: Smart Dispatcher

**Test**:
```elisp
SPC o c   ; or M-x ar/capture-dispatch
```

**Expected**: Prompt appears:
```
Capture: [t]ask [n]ote [f]leeting [j]ournal [q]uit?
```

### Test 10.2: Each Capture Option

**Task (t)**:
- Should call `org-gtd-capture`
- Opens GTD capture interface

**Note (n)**:
- Should call `org-roam-capture`
- Opens roam capture with templates

**Fleeting (f)**:
- Opens `fleeting.org`
- Prompts for thought
- Inserts at end of file

**Journal (j)**:
- Opens journal capture template
- Creates timestamped entry in journal.org

**Quit (q)**:
- Exits without capturing

### Test 10.3: Standard Captures

**Journal**: `SPC X` → `j`
**Meeting**: `SPC X` → `m`
**Book**: `SPC X` → `b`
**Habit**: `SPC X` → `h`
**Task**: `SPC X` → `t`

**Verify each template**:
- Correct file destination
- Proper headers/tags
- PROPERTIES drawer where applicable
- Clock-in for meetings

---

## Phase 11: Font Faces

### Test 11.1: Heading Sizes

**Create test file**:
```org
* Level 1 Heading
** Level 2 Heading
*** Level 3 Heading
**** Level 4 Heading
***** Level 5 Heading
****** Level 6 Heading
******* Level 7 Heading
******** Level 8 Heading
```

**Expected**:
- Level 1: Largest (1.20x)
- Level 2: 1.13x
- Decreasing sizes to Level 8
- All bold
- All use Doom font

### Test 11.2: List Bullets

**Test**:
```org
- Item 1
- Item 2
  - Sub-item
```

**Expected**: Hyphens display as bullets (•)

---

## Phase 12: Additional Features

### Test 12.1: Org Habit

**Create habit**:
```org
* TODO Daily Exercise
SCHEDULED: <2026-01-19 Mon .+1d>
:PROPERTIES:
:STYLE: habit
:END:
```

**In agenda**:
- Graph appears (21 days back, 7 forward)
- Custom glyphs if nerd-icons loaded
- Completion tracked

### Test 12.2: Org Download

**Drag image** into org file.

**Expected**:
- Image copied to `assets/` subdirectory
- Link inserted with timestamp
- Inline preview (if enabled)

**Screenshot** (if on Wayland with grim/slurp/swappy):
```elisp
M-x org-download-screenshot
```

### Test 12.3: Org Remark

**Highlight text**:
1. Select text
2. `M-x org-remark-mark`

**Expected**:
- Text highlighted
- Remark file created
- Can add notes to highlight

### Test 12.4: Org Pomodoro

1. Create task
2. `M-x org-pomodoro`

**Expected**:
- Timer starts
- Mode line shows countdown
- Notification at end (if notification system available)

### Test 12.5: Org Noter

**Prerequisites**: PDF file, `:tools pdf` module

1. Open PDF
2. `M-x org-noter`

**Expected**:
- PDF in one window
- Notes in split window
- Synced scrolling

### Test 12.6: Src Buffer Naming

**Test**:
1. Create src block
2. `SPC m '` (edit special)

**Expected**: Buffer named "src code" (not long descriptive name)

---

## Phase 13: Integration Testing

### Test 13.1: Complete GTD Workflow

1. **Capture task**: `SPC X` → `t` → "Buy groceries"
2. **Process inbox**: `SPC a i`
3. **Organize**: Move to next actions
4. **View in agenda**: `SPC o A` → `d`
5. **Complete task**: Mark as DONE
6. **Archive**: `SPC m A`

**Expected**: Full workflow works smoothly.

### Test 13.2: Complete Zettelkasten Workflow

1. **Capture fleeting**: `SPC o c` → `f` → idea
2. **Process to permanent**: `SPC o f` → review fleeting notes
3. **Create zettel**: `SPC n r f` → `z` template
4. **Link notes**: `SPC n r i` → connect to other notes
5. **Visualize**: `SPC n r u` → see graph
6. **Search**: `SPC n r s` → find information

**Expected**: Seamless note-taking workflow.

### Test 13.3: Project Bridge Workflow

1. **Create GTD project**: In `~/org/gtd/projects.org`
2. **Bridge to zettel**: `SPC n g`
3. **Work in zettel**: Add research, notes, insights
4. **Extract tasks**: `SPC n z`
5. **Tasks in inbox**: Verify in `~/org/gtd/inbox.org`

**Expected**: Smooth knowledge-to-action pipeline.

---

## Performance Testing

### Test 14.1: Startup Time

```bash
# Test Emacs startup
emacs --debug-init
```

**Expected**:
- Loads without errors
- Org-roam db sync delayed (idle timer)
- Org-gtd mode delayed (idle timer)
- No noticeable lag

### Test 14.2: Large File Handling

```bash
# Create large org file
for i in {1..1000}; do
  echo "* TODO Task $i" >> ~/org/test-large.org
done
```

**Open and test**:
- Folding/unfolding
- Agenda generation
- Search

**Expected**: Smooth performance, no lag.

---

## Troubleshooting

### Issue: org-gtd not found

**Fix**:
```elisp
M-x package-install RET org-gtd RET
doom sync
```

### Issue: org-roam database errors

**Fix**:
```bash
rm ~/.doom.d/.local/cache/org-roam.db
# In Emacs:
M-x org-roam-db-sync
```

### Issue: Transient menu doesn't appear when pressing <

**Diagnose**:
```elisp
M-x describe-key
# Press <
```

Should show: `ar/org-template-transient` or lambda function.

**Fix**: Check that org-mode-map binding is set correctly.

### Issue: Babel languages not loading

**Check**:
```elisp
M-x describe-variable RET org-babel-load-languages RET
```

**Fix**:
```elisp
M-x org-babel-do-load-languages RET
```

### Issue: GTD keywords not cycling properly

**Check**:
```elisp
M-x describe-variable RET org-todo-keywords RET
```

Should show all 3 sequences.

---

## Complete Checklist

- [ ] All packages installed (edna, gtd, remark, roam-ui, consult-org-roam)
- [ ] All directories created automatically
- [ ] All essential files exist with templates
- [ ] Org-tempo works (`<s TAB`)
- [ ] Custom templates work (`<sh TAB`, etc.)
- [ ] Transient template menu appears with `<`
- [ ] Babel executes code without confirmation
- [ ] Org-GTD commands work
- [ ] GTD keywords cycle properly
- [ ] Org-roam database syncs
- [ ] All roam templates work (zettel, literature, project, fleeting)
- [ ] Daily notes work
- [ ] Org-roam-ui opens and displays graph
- [ ] Consult-org-roam search works
- [ ] GTD → Zettel bridge creates notes correctly
- [ ] Zettel → GTD bridge extracts tasks
- [ ] Fleeting notes accessible
- [ ] Weekly review generates with counts
- [ ] All custom agenda views work
- [ ] Capture dispatcher works
- [ ] All individual capture templates work
- [ ] Font sizes scale for headings
- [ ] List bullets display as •
- [ ] Habits track and display graph
- [ ] Org-download works
- [ ] Org-remark highlights text
- [ ] Org-pomodoro timer works
- [ ] Org-noter syncs PDF and notes (if using)
- [ ] Src buffers named "src code"
- [ ] All keybindings work
- [ ] No errors in *Messages* buffer
- [ ] Performance is good with large files

**If all checked**: Configuration is fully functional! 🎉

---

## Support

If issues persist:

1. `doom doctor` - Check for problems
2. `doom clean` - Clean compiled files
3. `doom sync` - Resync packages
4. `doom compile` - Recompile
5. Check `*Messages*` buffer for errors
6. Enable debug: `M-x toggle-debug-on-error`

Enjoy your powerful Doom Emacs org-mode setup!
