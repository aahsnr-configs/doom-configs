;;; org-src-context.el --- LSP and Context support for org-src buffers -*- lexical-binding: t; -*-

;; Copyright (C) 2025  Ahsanur Rahman
;; Author: Ahsanur Rahman
;; Keywords: tools, languages, extensions, lsp
;; Package-Requires: ((emacs "30.1") (org "9.6"))
;; Version: 0.9.3

;;; Commentary:
;; This package injects surrounding source blocks into the `org-edit-special'
;; buffer to provide context for LSP servers (Eglot).
;;
;; ARCHITECTURAL OVERVIEW & DESIGN DECISIONS:
;;
;; 1. Unified Collector Strategy:
;;    Previous versions relied on `org-babel-tangle-collect-blocks`, which relies
;;    on cached properties and can fail if the file isn't saved.
;;    This version uses `org-babel-map-src-blocks` to scan the buffer directly.
;;    It explicitly matches blocks based on:
;;    a) Language: (e.g., Python blocks only see other Python blocks).
;;    b) Tangle Target: Handles complex inheritance. If a block inherits
;;       ":tangle script.py" from a property drawer, it is correctly grouped
;;       with other blocks targeting "script.py".
;;
;; 2. Lazy Execution & Command Whitelisting (Robustness):
;;    The package advises `org-edit-src-code`. This function is frequently called
;;    internally by Org Mode (for indentation/evaluation) and by external
;;    packages (like `evil-commentary`).
;;    To prevent breaking these operations or hanging the editor:
;;    a) Arg Check: If the `code` argument is present, SKIP (Transient op).
;;    b) Command Check: We strictly whitelist `org-edit-special` and its aliases.
;;       If the user did not explicitly ask to open the Edit Buffer, we do NOT
;;       run the context injection logic.
;;
;; 3. Marker-Based Tracking (Stability):
;;    We use Emacs Markers instead of integer positions to track the boundaries
;;    of injected context. Markers automatically update their indices when text
;;    is inserted or deleted. This prevents "off-by-one" errors where the
;;    narrowing window would snap to the wrong line during editing.
;;
;; 4. Safe Exit (Data Integrity):
;;    We attach cleanup hooks to both `org-edit-src-exit` (Save) and `abort`.
;;    This ensures the injected "ghost text" is deleted before Org writes the
;;    buffer content back to the main Org file, preventing code duplication.
;;
;; 5. Extension Mapping & Elisp Exclusion:
;;    LSP servers (like Pyright) require valid file extensions to activate.
;;    We map the Org language (e.g., "python") to its extension (".py").
;;    Crucially, we EXCLUDE Emacs Lisp from Eglot activation to prevent conflicts.

;;; Code:

(require 'org)
(require 'ob)
(require 'ob-tangle)
(require 'org-src)
(require 'cl-lib)

(defgroup org-src-context nil
  "Provide LSP support in org-src buffers."
  :group 'org)

;;; --- Customization Variables ---

(defcustom org-src-context-narrow-p t
  "Non-nil means org-src buffers should be narrowed to the editable block.
We recommend T to keep the context visual noise low, while still allowing
LSP to 'see' the invisible text.
If set to nil, the injected context is visible but read-only."
  :type 'boolean
  :group 'org-src-context)

(defcustom org-src-context-max-filesize 500000
  "Max size (in bytes) of an Org file to attempt context collection.
If the buffer is larger than this, context injection is skipped to prevent
editor freeze (lag) during the context collection phase."
  :type 'integer
  :group 'org-src-context)

;;; --- Internal State ---

;; We use Markers to define the editable region.
;; HEAD marker: Placed at the end of the injected header (Context Above).
;; TAIL marker: Placed at the start of the injected footer (Context Below).
(defvar-local org-src-context--head-marker nil)
(defvar-local org-src-context--tail-marker nil)

;;; --- Core Logic: Context Collection ---

(defun org-src-context--get-context-blocks (src-info)
  "Collect relevant context blocks (PREV . NEXT) for SRC-INFO.
Uses a unified strategy: scan buffer and match Language + Tangle target.
This function executes inside the ORIGINAL Org buffer.

Arguments:
  SRC-INFO: The list returned by `org-babel-get-src-block-info'.
            Format: (language body arguments switches name start inner-start inner-end)"
  (let* ((target-lang (nth 0 src-info))
         (target-params (nth 2 src-info))
         ;; Resolve the :tangle parameter. This handles inheritance from
         ;; file-wide properties (e.g. #+PROPERTY: header-args :tangle yes).
         ;; Defaults to "no" if not specified.
         (target-tangle (or (alist-get :tangle target-params) "no"))
         ;; Use Buffer Position (index 5 in light info), not Line Number.
         ;; Integer comparison is faster and less error-prone than line calculations.
         (current-blk-start (nth 5 src-info)))

    ;; OPTIMIZATION: Safety check for massive files.
    (if (> (buffer-size) org-src-context-max-filesize)
        (progn
          (message "Org-Src-Context: File too large (%d bytes), skipping context." (buffer-size))
          nil)

      (let ((prev nil)
            (next nil))
        ;; Scan entire buffer for matching blocks.
        ;; We scan the file on disk/buffer to ensure we catch all blocks,
        ;; even those not explicitly tangled yet (Literate workflow).
        (org-babel-map-src-blocks (buffer-file-name)
          (let* ((info (org-babel-get-src-block-info 'light))
                 (lang (nth 0 info))
                 (params (nth 2 info))
                 (tangle (or (alist-get :tangle params) "no"))
                 (blk-start (nth 5 info)))

            ;; MATCHING LOGIC:
            ;; 1. Language must match (e.g., Python vs Python).
            ;; 2. Tangle target must match.
            ;;    - If both are "no", they belong to the same 'notebook'.
            ;;    - If both are "script.py", they belong to that file.
            (when (and (string= lang target-lang)
                       (string= tangle target-tangle))

              ;; DEDUPLICATION LOGIC:
              ;; We strictly separate blocks into Previous or Next lists based on position.
              ;; IMPORTANT: We explicitly exclude the current block (where blk-start == current-blk-start)
              ;; to prevent code duplication in the edit buffer (LSP would see double definitions).
              (when (and (integerp blk-start) (integerp current-blk-start))
                (cond
                 ;; Previous Block
                 ((< blk-start current-blk-start)
                  (push info prev))
                 ;; Next Block
                 ((> blk-start current-blk-start)
                  (push info next))
                 ;; Current Block (Equal) -> Ignore/Exclude
                 (t nil))))))

        ;; Ordering Fix:
        ;; `org-babel-map-src-blocks` traverses the file top-down (A, B, C).
        ;; `push` adds to the front of the list, reversing the order (C, B, A).
        ;; We need `nreverse` to restore the correct file order (A, B, C) for injection.
        (cons (nreverse prev) (nreverse next))))))

(defun org-src-context--format-block (block)
  "Format a BLOCK list into a string for injection.
Takes the body (nth 1) and ensures it ends with a newline."
  (let ((body (nth 1 block)))
    (if (stringp body)
        (concat body "\n")
      "")))

;;; --- Core Logic: Injection & Properties ---

(defun org-src-context--inject (prev-blocks next-blocks)
  "Inject PREV-BLOCKS and NEXT-BLOCKS into the current (edit) buffer.
This function handles the delicate text properties required to prevent
'ghost newlines' and cursor jumping at boundaries."
  (let ((inhibit-read-only t)
        (inhibit-modification-hooks t))

    (save-excursion
      ;; 1. INJECT HEADER (Previous blocks)
      (goto-char (point-min))
      (let ((start (point)))
        (dolist (b prev-blocks)
          (insert (org-src-context--format-block b)))

        (unless (= start (point))
          (insert "\n") ;; Separator
          ;; STICKINESS EXPLANATION (The "Cursor Jump" Fix):
          ;; We set `rear-nonsticky (read-only)`.
          ;; If the user is at `point-min` (start of their code) and presses Backspace,
          ;; normally they would hit the read-only property of the header and get an error.
          ;; `rear-nonsticky` prevents the read-only property from "sticking" to the cursor
          ;; when moving backwards, allowing backspace to work at the boundary.
          (add-text-properties start (point)
                               '(read-only t
                                           font-lock-face shadow
                                           front-sticky t
                                           rear-nonsticky (read-only)
                                           org-src-context-block t))))

      ;; Set HEAD marker at the end of the injected header.
      ;; Insertion type NIL means: if text is inserted *at* this marker,
      ;; the marker stays *before* the new text. (Context stays above).
      (setq org-src-context--head-marker (point-marker))
      (set-marker-insertion-type org-src-context--head-marker nil)

      ;; 2. INJECT FOOTER (Next blocks)
      (goto-char (point-max))
      (let ((start (point)))
        (unless (bolp) (insert "\n")) ;; Ensure newline before footer
        (dolist (b next-blocks)
          (insert (org-src-context--format-block b)))

        (when (> (point) start)
          ;; STICKINESS EXPLANATION (The "Ghost Newline" Fix):
          ;; We set `front-sticky nil`.
          ;; If the user is at `point-max` (end of their code) and types text or RET,
          ;; normally the new characters might inherit the properties of the following text (the footer).
          ;; `front-sticky nil` ensures new text typed at this boundary is NOT read-only.
          (add-text-properties start (point)
                               '(read-only t
                                           font-lock-face shadow
                                           front-sticky nil
                                           rear-nonsticky t
                                           org-src-context-block t))))

      ;; Set TAIL marker at the start of the footer.
      ;; We scan backwards to find the exact boundary where the 'org-src-context-block' property starts.
      (let ((p (point-max)))
        (while (and (> p (point-min))
                    (get-text-property (1- p) 'org-src-context-block))
          (setq p (1- p)))
        (setq org-src-context--tail-marker (copy-marker p)))

      ;; Insertion type T means: if text is inserted *at* this marker,
      ;; the marker moves *after* the new text. (Context stays below).
      (set-marker-insertion-type org-src-context--tail-marker t)))

  ;; NARROWING
  ;; We narrow the buffer to the region between HEAD and TAIL markers.
  ;; This hides the context visually (if configured) but keeps it available for LSP.
  (when org-src-context-narrow-p
    (when (and org-src-context--head-marker org-src-context--tail-marker)
      (narrow-to-region org-src-context--head-marker org-src-context--tail-marker))))

;;; --- Core Logic: LSP Mocking ---

(defun org-src-context--setup-lsp (info original-dir original-file)
  "Configure buffer-local variables so Eglot can find the root.
Since org-src buffers are temporary and not file-backed, Eglot normally
refuses to start. We fix this by mocking a file path based on the Tangle target
or Language extension."
  (let* ((lang (nth 0 info))
         (params (nth 2 info))
         (tangle-file (alist-get :tangle params))
         ;; Determine correct extension (e.g., python -> .py) using Org's internal map
         (lang-ext (or (cdr (assoc lang org-babel-tangle-lang-exts)) "txt"))

         ;; EXTENSION LOGIC:
         ;; 1. Use extension from tangle file if available.
         ;; 2. Fallback to language extension if tangle is "no" or "yes".
         (file-ext (if (and tangle-file
                            (not (member tangle-file '("yes" "no")))
                            (file-name-extension tangle-file))
                       (file-name-extension tangle-file)
                     lang-ext))

         ;; FILENAME LOGIC:
         ;; 1. Use the explicit tangle filename if provided.
         ;; 2. Construct a mock name "original_src.ext" for literate notebooks.
         ;;    The file doesn't need to exist on disk, but the path must be inside the project.
         (mock-name (if (and tangle-file
                             (not (member tangle-file '("yes" "no"))))
                        tangle-file
                      (concat (file-name-base original-file) "_src." file-ext))))

    ;; Set default-directory to the project root (where the Org file lives).
    (setq-local default-directory original-dir)

    ;; Set buffer-file-name to the mocked path.
    ;; This allows Eglot to walk up the directory tree to find .git or project.toml.
    (setq-local buffer-file-name (expand-file-name mock-name original-dir))

    ;; Trigger Eglot initialization now that the "file" appears valid.
    ;; FIX: We EXCLUDE Emacs Lisp buffers. Elisp has native support and
    ;; forcing Eglot often causes errors or unnecessary server prompts.
    (when (and (fboundp 'eglot-ensure)
               (not (member lang '("emacs-lisp" "elisp"))))
      (eglot-ensure))))

;;; --- Advice & Hooks ---

(defun org-src-context--advice (orig-fn &rest args)
  "Advice for `org-edit-src-code'.
This is the entry point for the package.

1. PERF CHECK: Checks `(car args)` (the CODE argument).
   If CODE is non-nil, it means Org is performing an automated task
   (like indentation or export). We MUST return immediately.

2. COMMAND CHECK: We strictly whitelist the interactive commands `org-edit-special`
   and `org-edit-src-code` (and their aliases).
   If `this-command` is anything else (e.g., `org-return`, `comment-region`,
   `evil-commentary`), we SKIP context injection.
   This prevents the package from interfering with internal Org operations,
   specifically solving the 'Read-Only' bug when editing Elisp blocks in place.

3. COLLECT: If it is an interactive edit, we collect context blocks.

4. EXECUTE: We let `org-edit-src-code` create the buffer.

5. INJECT: We switch to the new buffer and inject the collected context."

  ;; ROBUSTNESS CHECK 1: Ignore transient calls (CODE arg present)
  ;; ROBUSTNESS CHECK 2: Command Whitelist (Only allow user-initiated edits)
  (if (or (car args)
          (not (memq this-command '(org-edit-special 
                                    org-edit-src-code 
                                    evil-org-edit-src-code))))
      (apply orig-fn args)

    ;; REAL EDIT SESSION
    (let* ((datum (org-element-context))
           (type (org-element-type datum)))
      ;; Only proceed if we are actually at a source block
      (if (not (eq type 'src-block))
          (apply orig-fn args)

        (let* ((info (org-babel-get-src-block-info 'light))
               ;; 1. Collect Context (While still in Org Buffer)
               ;; This will respect inherited PROPERTIES automatically.
               (context-blocks (org-src-context--get-context-blocks info))
               (orig-dir default-directory)
               (orig-file (buffer-file-name)))

          ;; 2. Create Edit Buffer (standard Org behavior)
          (apply orig-fn args)

          ;; 3. We are now in the Edit Buffer. Inject!
          (when context-blocks
            (org-src-context--inject (car context-blocks) (cdr context-blocks)))

          ;; 4. Setup LSP Mocking
          (org-src-context--setup-lsp info orig-dir orig-file))))))

(defun org-src-context--cleanup (&rest _)
  "Clean up narrowing and markers before exiting or aborting.
This is CRITICAL: We must remove injected text before Org saves the buffer
back to the main Org file. If we don't, the injected context will be
pasted into your source block, duplicating code."
  (let ((inhibit-read-only t)
        (inhibit-modification-hooks t))
    (ignore-errors
      (widen)
      ;; Delete the header region
      (when (and org-src-context--head-marker (marker-buffer org-src-context--head-marker))
        (delete-region (point-min) org-src-context--head-marker)
        (set-marker org-src-context--head-marker nil))

      ;; Delete the footer region
      (when (and org-src-context--tail-marker (marker-buffer org-src-context--tail-marker))
        (delete-region org-src-context--tail-marker (point-max))
        (set-marker org-src-context--tail-marker nil)))))

;;;###autoload
(define-minor-mode org-src-context-mode
  "Global mode to inject context into Org Src buffers for LSP.

**Performance Optimized** version by Ahsanur Rahman.

When enabled:
1. Advise `org-edit-src-code` to inject context and setup LSP.
2. Advise `org-edit-src-exit` and `abort` to cleanup injected context."
  :global t
  :group 'org-src-context
  (if org-src-context-mode
      (progn
        ;; Add the main logic
        (advice-add 'org-edit-src-code :around #'org-src-context--advice)
        ;; Add safety cleanup hooks on both exit paths (Save or Abort)
        (advice-add 'org-edit-src-exit :before #'org-src-context--cleanup)
        (advice-add 'org-edit-src-abort :before #'org-src-context--cleanup))
    ;; Remove everything on disable
    (advice-remove 'org-edit-src-code #'org-src-context--advice)
    (advice-remove 'org-edit-src-exit #'org-src-context--cleanup)
    (advice-remove 'org-edit-src-abort #'org-src-context--cleanup)))

(provide 'org-src-context)
;;; org-src-context.el ends here
