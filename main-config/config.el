(setq user-full-name "Ahsanur Rahman"
      user-mail-address "ahsanur041@proton.me")

;; (global-so-long-mode 1)
(size-indication-mode -1)
(global-prettify-symbols-mode 1)

(after! evil
  (setq evil-want-fine-undo t
        evil-vsplit-window-right t
        evil-split-window-below t
        evil-move-beyond-eol t
        evil-ex-substitute-global t
        evil-move-cursor-back nil
        evil-kill-on-visual-paste nil))

(after! evil-escape
  (setq evil-escape-key-sequence "jk"
        evil-escape-delay 0.2))

;; Use visual line navigation, which is more intuitive when working with wrapped lines.
(map! :nv "j" #'evil-next-visual-line
      :nv "k" #'evil-previous-visual-line)

(setq-default internal-border-width 5)
(add-to-list 'default-frame-alist '(internal-border-width . 5))

(setq-default indent-tabs-mode nil
              tab-width 2
              fill-column 80
              line-spacing 0.02)

(setq confirm-kill-emacs nil)

(setq hscroll-step 1
      hscroll-margin 2
      scroll-step 1
      scroll-margin 0
      scroll-conservatively 101
      scroll-preserve-screen-position t
      auto-window-vscroll nil
      mouse-wheel-scroll-amount-horizontal 1
      mouse-wheel-progressive-speed nil)

(setq inhibit-compacting-font-caches t)
(setq warning-suppress-types '((org-element)))

(setq split-width-threshold 170
      split-height-threshold nil)

(setq-default bidi-inhibit-bpa t) ;; Emacs 27+ recommended
(setq-default bidi-display-reordering nil)

(set-selection-coding-system 'utf-8)
(prefer-coding-system 'utf-8)
(set-language-environment "UTF-8")
(set-default-coding-systems 'utf-8)
(set-terminal-coding-system 'utf-8)
(set-keyboard-coding-system 'utf-8)
(setq locale-coding-system 'utf-8)

(when (display-graphic-p)
  (setq x-select-request-type '(UTF8_STRING COMPOUND_TEXT TEXT STRING)))

(use-package! doom-themes
  :custom
  (doom-themes-enable-bold t)
  (doom-themes-enable-italic t)
  (doom-themes-treemacs-theme "doom-colors")
  :config
  (load-theme 'doom-tokyo-night t)
  (doom-themes-visual-bell-config)
  (doom-themes-neotree-config)
  (doom-themes-treemacs-config)
  (doom-themes-org-config))

;; (use-package! catppuccin-theme
;;   :config
;;   (setq catppuccin-flavor 'mocha)
;;   ;; Enable Catppuccin quality-of-life features
;;   (setq catppuccin-italic-comments t
;;         catppuccin-italic-blockquotes t
;;         catppuccin-italic-variables nil
;;         catppuccin-highlight-matches t
;;         catppuccin-dark-line-numbers-background t)

;;   (setq doom-theme 'catppuccin)

;;   (custom-theme-set-faces! 'catppuccin
;;     '(default :background "#1e1e2e" :foreground "#cdd6f4")
;;     '(corfu-default :background "#1e1e2e" :foreground "#cdd6f4")
;;     '(solaire-mode-bg-face :background "#11111b")
;;     '(hl-line :background "#11111b" :extend t)
;;     '(org-block :background "#313244" :foreground "#cdd6f4" :extend t)
;;     '(org-block-begin-line :background "#313244" :foreground "#6c7086" :extend t)
;;     '(org-block-end-line :background "#313244" :foreground "#6c7086" :extend t)
;;     '(org-meta-line :foreground "#6c7086")
;;     '(org-document-info-keyword :foreground "#6c7086")
;;     '(mode-line :background "#181825" :foreground "#cdd6f4")
;;     '(mode-line-inactive :background "#11111b" :foreground "#6c7086")
;;     '(region :background "#585b70" :extend t)
;;     '(cursor :background "#f5e0dc")
;;     '(show-paren-match :foreground "#f5c2e7" :background "#45475a" :weight bold)
;;     '(sp-show-pair-match-face :background "#b4befe" :foreground "black")
;;     '(minibuffer-prompt :foreground "#89dceb" :weight bold)
;;     '(pdf-view-highlight-face :background "#f9e2af" :foreground "#1e1e2e")
;;     '(pdf-view-link-face :foreground "#89b4fa")
;;     '(pdf-view-active-link-face :foreground "#cba6f7"))


;;   )

(add-hook! 'doom-first-buffer-hook
  (size-indication-mode -1)
  (setq-default mode-line-percent-position nil))

(after! doom-modeline
  (setq doom-modeline-height 25
        doom-modeline-column-zero-based nil
        doom-modeline-bar-width 3
        doom-modeline-buffer-file-size nil
        doom-modeline-buffer-file-name-style 'file-name
        doom-modeline-buffer-encoding nil
        doom-modeline-percent-position nil
        doom-modeline-major-mode-icon t
        doom-modeline-major-mode-color-icon t
        doom-modeline-vcs-icon t
        doom-modeline-vcs-max-length 0))

;; Enable absolute line numbers globally by default.
(setq display-line-numbers-type t)
(setq display-line-numbers-width 4)

;; Disable line numbers in modes where they aren't useful.
(add-hook! '(org-mode-hook
             dired-mode-hook
             magit-status-mode-hook
             eshell-mode-hook
             vterm-mode-hook
             help-mode-hook
             doom-dashboard-mode-hook)
           #'(lambda () (display-line-numbers-mode -1)))

;; ALTERNATE CODE
;; (remove-hook! '(text-mode-hook org-mode-hook) #'display-line-numbers-mode)

;; (add-hook! (prog-mode
;;             conf-mode
;;             toml-ts-mode
;;             yaml-mode
;;             yaml-ts-mode)
;;   #'display-line-numbers-mode)

(setq doom-font (font-spec :family "JetBrains Mono" :size 13.0 :weight 'medium)
      doom-variable-pitch-font (font-spec :family "JetBrains Mono" :size 13.0)
      doom-big-font (font-spec :family "JetBrains Mono" :size 24))

(use-package! rainbow-delimiters
  :hook ((text-mode . rainbow-delimiters-mode)
         (LaTeX-mode . rainbow-delimiters-mode)
         (org-src-mode . rainbow-delimiters-mode)
         (prog-mode . rainbow-delimiters-mode)))

(custom-set-faces!
 '(rainbow-delimiters-depth-1-face :foreground "#89b4fa")
 '(rainbow-delimiters-depth-2-face :foreground "#cba6f7")
 '(rainbow-delimiters-depth-3-face :foreground "#f9e2af")
 '(rainbow-delimiters-depth-4-face :foreground "#89dceb")
 '(rainbow-delimiters-depth-5-face :foreground "#f38ba8")
 '(rainbow-delimiters-depth-6-face :foreground "#a6e3a1")
 '(rainbow-delimiters-depth-7-face :foreground "#fab387")
 '(rainbow-delimiters-depth-8-face :foreground "#cdd6f4")
 '(rainbow-delimiters-depth-9-face :foreground "#bac2de"))

(use-package! rainbow-mode
  :hook ((prog-mode . rainbow-mode)
         (org-mode . rainbow-mode)))

;;; Alternate code
;; (use-package! rainbow-mode
;;   :hook ((prog-mode . rainbow-mode)
;;          (LaTeX-mode . rainbow-mode)
;;          (org-mode . rainbow-mode))
;;   :config
;;   (setq rainbow-html-colors t)
;;   (setq rainbow-x-colors t)
;;   (setq rainbow-latex-colors t))

(after! which-key
  (setq which-key-idle-delay 0.3
        which-key-allow-imprecise-window-fit nil
        which-key-separator " → "
        which-key-max-display-columns nil
        which-key-popup-type 'side-window
        which-key-side-window-max-width 0.33))

(after! smartparens
  ;; Enable show-smartparens-mode globally
  (show-smartparens-global-mode +1)
  (add-hook 'prog-mode-hook #'doom-disable-show-paren-mode-h)
  ;; But disable it in large files to prevent performance issues
  (add-hook 'prog-mode-hook
            (lambda ()
              (when (> (buffer-size) 40000)
                (show-smartparens-mode -1)))))

(after! indent-bars
  (setq indent-bars-color '(highlight :face-bg t :blend 0.165)
        indent-bars-no-descend-string t
        indent-bars-prefer-character t
        indent-bars-highlight-current-depth '(:face default :blend 0.85)
        indent-bars-depth-update-delay 0.075))

;; ;; Disable in Org mode
;; (add-hook 'org-mode-hook
;;   (lambda ()
;;     (when (bound-and-true-p indent-bars-mode)
;;       (indent-bars-mode -1))))

;; (defun +indent-bars-disable-in-visual-h ()
;;   "Disable indent-bars-mode when entering Evil visual state."
;;   (when (bound-and-true-p indent-bars-mode)
;;     (indent-bars-mode -1)
;;     (setq-local +indent-bars-was-enabled t)))

;; (defun +indent-bars-enable-after-visual-h ()
;;   "Re-enable indent-bars-mode when exiting Evil visual state."
;;   (when (bound-and-true-p +indent-bars-was-enabled)
;;     (indent-bars-mode 1)
;;     (kill-local-variable '+indent-bars-was-enabled)))

;; (add-hook 'evil-visual-state-entry-hook #'+indent-bars-disable-in-visual-h)
;; (add-hook 'evil-visual-state-exit-hook #'+indent-bars-enable-after-visual-h)


(use-package! dtrt-indent
  :config
  (dtrt-indent-global-mode 1)
  ;; Optional: Adjust verbosity
  ;; 0 = silent, 1 = notify on change (default), 2 = explain why not changed, 3 = debug
  (setq dtrt-indent-verbosity 1)
  ;; Optional: Set minimum confidence threshold
  ;; Only adjust if dtrt-indent is confident in its detection
  (setq dtrt-indent-min-quality 100)

  ;; Optional: Exclude certain modes where you want manual control
  (setq dtrt-indent-mode-exclude-list '(org-mode)))

(use-package! sudo-edit
  :commands sudo-edit)

(setq resize-mini-windows t)
(set-popup-rule! "^ \\*transient*" :ignore t)

(after! transient
  (require 'nerd-icons)

  (defun +toggles/main-title ()
    (concat
     (if (fboundp 'nerd-icons-faicon)
         (nerd-icons-faicon "nf-fa-toggle_on" :face 'transient-heading :v-adjust 0.02)
       "")
     (propertize " Doom Toggles" 'face 'transient-heading)))

  (defun +toggles/toggle-whitespace ()
    (interactive)
    (setq show-trailing-whitespace (not show-trailing-whitespace))
    (redraw-display)
    (message "Trailing whitespace %s" (if show-trailing-whitespace "ON" "OFF")))

  (transient-define-prefix +toggles/main ()
    "Global Toggles and Actions"
    [:description +toggles/main-title

     ["Basic"
      ("n" "Line numbers" doom/toggle-line-numbers :transient t)
      ("a" "Aggressive indent" global-aggressive-indent-mode :transient t
       :if (lambda () (fboundp 'global-aggressive-indent-mode)))
      ("d" "Hungry delete" global-hungry-delete-mode :transient t
       :if (lambda () (fboundp 'global-hungry-delete-mode)))
      ("e" "Electric pair" electric-pair-mode :transient t)
      ("c" "Spell check" flyspell-mode :transient t
       :if (lambda () (featurep 'flyspell)))
      ("s" "Pretty symbol" prettify-symbols-mode :transient t)
      ("l" "Page break lines" global-page-break-lines-mode :transient t
       :if (lambda () (fboundp 'global-page-break-lines-mode)))
      ("b" "Battery" display-battery-mode :transient t)
      ("i" "Time" display-time-mode :transient t)
      ("m" "Modeline" (lambda () (interactive)
                        (if (bound-and-true-p doom-modeline-mode)
                            (doom-modeline-mode -1)
                          (doom-modeline-mode 1)))
       :transient t :if (lambda () (featurep 'doom-modeline)))]

      ["Highlight"
       ("h l" "Line" global-hl-line-mode :transient t)
       ("h p" "Paren" show-paren-mode :transient t)
       ("h s" "Symbol" symbol-overlay-mode :transient t
        :if (lambda () (fboundp 'symbol-overlay-mode)))
       ("h r" "Rainbow" rainbow-mode :transient t
        :if (lambda () (fboundp 'rainbow-mode)))
       ("h w" "Whitespace" +toggles/toggle-whitespace :transient t)
       ("h d" "Delimiters" rainbow-delimiters-mode :transient t
        :if (lambda () (fboundp 'rainbow-delimiters-mode)))
       ("h i" "Indent guides" highlight-indent-guides-mode :transient t
       :if (lambda () (fboundp 'highlight-indent-guides-mode)))
       ("h t" "Todo" global-hl-todo-mode :transient t
        :if (lambda () (fboundp 'global-hl-todo-mode)))]

      ["Program"
       ("f" "Flymake" flymake-mode :transient t)
       ("O" "Hideshow" hs-minor-mode :transient t)
       ("u" "Subword" subword-mode :transient t)
       ("W" "Which func" which-function-mode :transient t)
       ("E" "Debug on error" toggle-debug-on-error :transient t)
       ("Q" "Debug on quit" toggle-debug-on-quit :transient t)
       ("v" "Gutter" global-diff-hl-mode :transient t
        :if (lambda () (modulep! :ui vc-gutter)))
       ("V" "Live gutter" diff-hl-flydiff-mode :transient t
        :if (lambda () (and (modulep! :ui vc-gutter) (fboundp 'diff-hl-flydiff-mode))))]

     ["Package"
      ("p r" "Refresh archives" package-refresh-contents)
      ("p l" "List packages" package-list-packages)
      ("p i" "Install package" package-install)
      ("p d" "Delete package" package-delete)
      ("p a" "Autoremove" package-autoremove)
      ;; HIDDEN TOGGLE KEY:
      ("<f6>" "" transient-quit-one :format " ")]]))

;; 3. BINDING
(map! :g "<f6>" #'+toggles/main)

(map! :leader
      :desc "M-x" "SPC" #'execute-extended-command)

(use-package! page-break-lines
  :init
  ;; `derived-mode-p' walks the mode ancestry, so prog-mode covers
  ;; emacs-lisp-mode, python-mode, etc. and text-mode covers org-mode,
  ;; markdown-mode, outline-mode, etc.
  (setq page-break-lines-modes
        '(prog-mode
          text-mode
          help-mode
          compilation-mode))

  ;; Character drawn to form the rule (set in :init so defcustom's defvar
  ;; cannot override it).  Alternatives: ?━ heavy  ?═ double  ?- ASCII
  (setq page-break-lines-char ?─)

  ;; (setq page-break-lines-max-width 80) ; cap rule width; nil = full window
  ;; (setq page-break-lines-lighter "")   ; hide the mode-line indicator

  :config
  (global-page-break-lines-mode 1)

  ;; Uncomment if rules appear the wrong width (M-x describe-char on ^L
  ;; to check which font is being used for U+2500):
  ;; (set-fontset-font "fontset-default"
  ;;                   (cons page-break-lines-char page-break-lines-char)
  ;;                   (face-attribute 'default :family))
  )

;; Use custom-set-faces! (not set-face-attribute) so the setting survives
;; theme changes.  Uncomment to override the default comment-face inherit:
;; (custom-set-faces!
;;   '(page-break-lines :inherit font-lock-comment-face
;;                      :weight normal :slant normal))

;; SPC t P — toggle page-break-lines-mode in the current buffer.
(map! :leader
      :desc "Toggle page-break-lines" "t P" #'page-break-lines-mode)

(map! "M-$"   #'jinx-correct    ; replaces ispell-word; upstream recommendation
      "C-M-$" #'jinx-languages) ; change language(s) for the current buffer

(use-package! jinx
  :hook (doom-first-buffer . global-jinx-mode)

  :init
  (setq jinx-languages "en_US")

  :config
  (put 'jinx-local-words 'safe-local-variable #'stringp)

  (setf (alist-get 'prog-mode jinx-include-faces)
        '(font-lock-comment-face
          font-lock-doc-face))

  (setf (alist-get 'org-mode jinx-exclude-faces)
        (append (alist-get 'org-mode jinx-exclude-faces)
                '(org-level-1 org-level-2 org-level-3 org-level-4
                  org-level-5 org-level-6 org-level-7 org-level-8)))

  (after! vertico-multiform
    (add-to-list 'vertico-multiform-categories
                 '(jinx grid
                        (vertico-grid-annotate . 20)
                        (vertico-count . 4))))

  (when (modulep! :editor evil)
    (map! :map jinx-mode-map
          :n "zg" #'jinx-correct
          :n "z=" #'jinx-correct
          :n "[s" #'jinx-previous
          :n "]s" #'jinx-next)))

(after! dired
  (setq dired-listing-switches "-agho --group-directories-first"
        delete-by-moving-to-trash t
        dired-dwim-target t))

(use-package! dired-open
  :after dired
  :config
  (setq dired-open-extensions '(("png" . "imv")
                                ("mp4" . "mpv"))))

(after! vertico
  (setq vertico-count 12))

(after! projectile
  (setq projectile-project-root-files-bottom-up
        '(".projectile" ".git"))
  (setq projectile-indexing-method 'alien)
  (setq projectile-enable-caching t)
  (advice-add 'projectile-find-file :around
              (lambda (orig-fun &rest args)
                (let ((default-directory (projectile-project-root)))
                  (apply orig-fun args)))))

(defvar my/org-directory "~/org/" "The root directory for Org files.")
(defvar my/org-roam-directory (expand-file-name "roam/" my/org-directory) "The directory for Org Roam files.")

(after! org
  (add-hook! 'org-mode-hook #'(lambda () (org-indent-mode -1)))
  (add-hook! 'org-babel-after-execute-hook #'org-redisplay-inline-images)

  (setq org-directory my/org-directory
        org-agenda-files (list (expand-file-name "inbox.org" my/org-directory)
                               (expand-file-name "projects.org" my/org-directory)
                               (expand-file-name "habits.org" my/org-directory))
        org-default-notes-file (expand-file-name "inbox.org" my/org-directory)

        org-src-fontify-natively t
        org-hide-emphasis-markers nil
        org-hide-leading-stars nil
        ;; org-fontify-quote-and-verse-blocks nil
        ;; org-fontify-whole-heading-line nil
        ;; org-fontify-done-headline nil
        ;; org-highlight-latex-and-related nil
        org-startup-folded 'showeverything
        org-cycle-separator-lines 2

        org-confirm-babel-evaluate nil

        org-element-use-cache t
        org-element-cache-persistent t

        org-agenda-inhibit-startup t
        org-agenda-dim-blocked-tasks nil
        org-agenda-use-tag-inheritance nil
        org-agenda-ignore-properties '(effort appt category)
        org-agenda-span 'day

        ;; Image settings
        ;; org-image-actual-width 600

         org-todo-keywords
        '((sequence "TODO(t)" "NEXT(n)" "PROG(p)" "WAIT(w@/!)" "|" "DONE(d!)" "CANCEL(c@)")
          (sequence "PLAN(P)" "ACTIVE(A)" "PAUSED(x)" "|" "ACHIEVED(a)" "DROPPED(D)"))

        org-archive-location (concat my/org-directory "archive/%s_archive::")
        org-todo-keywords
        '((sequence "TODO(t)" "NEXT(n)" "PROG(p)" "WAIT(w@/!)" "|" "DONE(d!)" "CANCEL(c@)")
          (sequence "PLAN(P)" "ACTIVE(A)" "PAUSED(x)" "|" "ACHIEVED(a)" "DROPPED(D)"))

        org-todo-keyword-faces
        '(("TODO"      . (:foreground "#f38ba8" :weight bold))
          ("NEXT"      . (:foreground "#fab387" :weight bold))
          ("PROG"      . (:foreground "#89b4fa" :weight bold))
          ("WAIT"      . (:foreground "#f9e2af" :weight bold))
          ("DONE"      . (:foreground "#a6e3a1" :weight bold))
          ("CANCEL"    . (:foreground "#6c7086" :weight bold))
          ("PLAN"      . (:foreground "#94e2d5" :weight bold))
          ("ACTIVE"    . (:foreground "#cba6f7" :weight bold))
          ("PAUSED"    . (:foreground "#bac2de" :weight bold))
          ("ACHIEVED"  . (:foreground "#a6e3a1" :weight bold))
          ("DROPPED"   . (:foreground "#6c7086" :weight bold)))))


(use-package! org-super-agenda
  :after org-agenda
  :hook (org-agenda-mode-hook . org-super-agenda-mode))

(after! org-modern
  (setq
   org-modern-hide-stars "· "
   org-modern-star '("◉" "○" "◈" "◇" "◆" "▷")
   org-modern-list '((43 . "➤") (45 . "–") (42 . "•"))
   org-modern-table-vertical 1
   org-modern-table-horizontal 0.1
   org-modern-block-name '(("src" "»" "«")
                           ("example" "»" "«")
                           ("quote" "❝" "❞"))
   org-modern-checkbox '((todo . "☐") (done . "☑") (cancel . "☒") (priority . "⚑") (on . "◉") (off . "○"))
   org-modern-tag-faces `((:foreground ,(face-attribute 'default :foreground) :weight bold :box (:line-width (1 . -1) :color "#45475a")))))

(defun ar/org-src-simplify-buffer-name (base-buffer-name lang)
  "Return static buffer name 'src code' for Org source blocks."
  "src code")

(advice-add 'org-src--construct-edit-buffer-name
            :override #'ar/org-src-simplify-buffer-name)

;; (after! ob-jupyter
;;   ;; Default header arguments for jupyter-python blocks
;;   (setq org-babel-default-header-args:jupyter-python
;;         '((:async . "yes")
;;           (:session . "py")
;;           (:kernel . "python3")
;;           (:exports . "both")
;;           (:results . "output")))

;;   ;; Override python blocks with jupyter AFTER ob-jupyter loads
;;   ;; This lets you use #+begin_src python instead of jupyter-python
;;   (org-babel-jupyter-override-src-block "python")

;;   ;; Resource directory for images and other outputs
;;   (setq org-babel-jupyter-resource-directory
;;         (expand-file-name ".jupyter-resources/" org-directory))

;;   ;; Pandoc integration for richer output rendering
;;   (when (executable-find "pandoc")
;;     (setq jupyter-org-pandoc-convertable
;;           '("text/html" "text/markdown" "text/latex"))))

;; ;; Ensure jupyter is properly loaded when executing python blocks
;; (add-hook! '+org-babel-load-functions
;;   (defun +jupyter-load-and-override-h (lang)
;;     "Load jupyter for python and apply overrides."
;;     (when (eq lang 'python)
;;       (require 'ob-jupyter nil t)
;;       (when (featurep 'ob-jupyter)
;;         (org-babel-jupyter-make-local-aliases)
;;         (org-babel-jupyter-override-src-block "python")))))

(after! magit
  (setq magit-display-buffer-function #'magit-display-buffer-same-window-except-diff-v1))

(use-package! magit-todos
  :after magit
  :config (magit-todos-mode 1))

(setq forge-owned-accounts '(("aahsnr")))

(after! vertico
  (setq vertico-count 10))

(with-eval-after-load 'python
  (set-eglot-client! '(python-mode python-ts-mode) '("pyrefly" "lsp"))
  (set-formatter! 'ruff :modes '(python-mode python-ts-mode)))

(setq +python-ipython-repl-args '("-i" "--simple-prompt" "--no-color-info"))
(setq +python-jupyter-repl-args '("--simple-prompt"))

(after! tex
  (setq TeX-engine 'luatex)
  (setq TeX-output-dir "build/")
  (setq LaTeX-command "latex -shell-escape")
  (setq TeX-save-query nil)
  (setq TeX-clean-confirm nil)
  (setq font-latex-fontify-script 'multi-level
        font-latex-fontify-sectioning 1.2))

(after! latex
  (add-to-list 'TeX-command-list
               '("LuaLaTeXmk" "latexmk -pdflua -pdflualatex='lualatex -shell-escape -interaction=nonstopmode' -f -outdir=%o %S"
                 TeX-run-TeX nil t
                 :help "Run latexmk with LuaLaTeX") t)

  ;; Add continuous preview mode (watch mode)
  (add-to-list 'TeX-command-list
               '("LaTeXmk-Watch" "latexmk -pvc -pdflua -pdflualatex='lualatex -shell-escape -interaction=nonstopmode' -outdir=%o %S"
                 TeX-run-TeX nil t
                 :help "Run latexmk in continuous preview mode") t)

  (setq-default TeX-command-default
                (cond ((eq TeX-engine 'luatex) "LuaLaTeXmk")
                      ((eq TeX-engine 'xetex) "XeLaTeXmk")
                      (t "LaTeXmk")))

  ;; Auxiliary files to clean
  (setq LaTeX-clean-intermediate-suffixes
        '("\\.aux" "\\.bbl" "\\.blg" "\\.brf" "\\.fot"
          "\\.glo" "\\.gls" "\\.idx" "\\.ilg" "\\.ind"
          "\\.lof" "\\.log" "\\.lot" "\\.nav" "\\.out"
          "\\.snm" "\\.toc" "\\.url" "\\.synctex\\.gz"
          "\\.fdb_latexmk" "\\.fls" "\\.xdv"
          "-blx\\.bib" "\\.run\\.xml"))

  )

;; Configure pdf-tools integration with AUCTeX
(setq +latex-viewers '(pdf-tools))
(after! tex
  (setq TeX-view-program-selection '((output-pdf "PDF Tools"))
        TeX-view-program-list '(("PDF Tools" TeX-pdf-tools-sync-view)))

  ;; Automatically revert PDF buffer after compilation
  (add-hook 'TeX-after-compilation-finished-functions
            #'TeX-revert-document-buffer))

(after! org
  (add-to-list 'org-preview-latex-process-alist
               '(luamagick
                 :programs ("lualatex" "magick")
                 :description "pdf > png"
                 :message "you need to install lualatex and imagemagick."
                 :use-xcolor t
                 :image-input-type "pdf"
                 :image-output-type "png"
                 :image-size-adjust (1.0 . 1.0)
                 :latex-compiler ("lualatex -interaction nonstopmode -output-directory %o %f")
                 :image-converter ("magick convert -density 130 -trim -antialias %f -quality 100 %O")))

  ;; Set default preview process
  (setq org-preview-latex-default-process 'luamagick)

  ;; Preview appearance settings
  (setq org-format-latex-options
        (plist-put org-format-latex-options :scale 2.0))
  (setq org-format-latex-options
        (plist-put org-format-latex-options :foreground 'default))
  (setq org-format-latex-options
        (plist-put org-format-latex-options :background 'default))

  ;; Directory for preview images
  (setq org-preview-latex-image-directory "ltximg/")

  ;; LaTeX packages for preview
  ;; These are added to org-latex-packages-alist in the LaTeX section
  ;; but we ensure they're available for preview too
  (setq org-latex-packages-alist
        '(("" "fontspec" t ("lualatex" "xelatex"))
          ("" "unicode-math" t ("lualatex" "xelatex"))
          ("" "amsmath" t)
          ("" "amssymb" t)
          ("" "mathtools" nil))))

(use-package! org-fragtog
  :hook (org-mode . org-fragtog-mode)
  :config
  (setq org-fragtog-preview-delay 0.2))

;; Alternative for Org 9.7+ users (uncomment if using newer Org):
;;(after! org
   ;; Use the new built-in preview system
;;   (add-hook 'org-mode-hook 'org-latex-preview-auto-mode)
;;   (setq org-latex-preview-live t)
;;   (setq org-latex-preview-auto-mode-inline-preview-delay 0.25))

(map! :after latex
      :map LaTeX-mode-map
      :localleader
      ;; We extend with latexmk-specific commands
      (:prefix ("b" . "build")
       :desc "Compile with latexmk" "m" (cmd! (TeX-command "LuaLaTeXmk" 'TeX-master-file))
       :desc "Watch mode (continuous)" "w" (cmd! (TeX-command "LaTeXmk-Watch" 'TeX-master-file))
       :desc "View output" "v" #'TeX-view
       :desc "Clean auxiliary files" "k" #'TeX-clean)

      ;; Citation management (extends Doom's citar keybindings)
      (:prefix ("r" . "references")
       :desc "Insert citation" "i" #'citar-insert-citation
       :desc "Open citation" "o" #'citar-open
       :desc "Open library file" "f" #'citar-open-library-file
       :desc "Open notes" "n" #'citar-open-notes
       :desc "Create note" "N" #'citar-create-note
       :desc "Setup project bib" "b" #'+latex-setup-project-bibliography))

;; Org-mode LaTeX keybindings
(map! :after org
      :map org-mode-map
      :localleader
      (:prefix ("L" . "LaTeX")
       :desc "Preview fragment" "p" #'org-latex-preview
       :desc "Export to PDF" "e" #'org-latex-export-to-pdf
       :desc "Toggle fragtog" "f" #'org-fragtog-mode))

(use-package! lsp-nix
  :after (lsp-mode)
  :custom
  (lsp-nix-nil-formatter ["alejandra"]))

(use-package! nix-mode
  :hook (nix-mode . lsp-deferred))

(use-package! nix-ts-mode
 :mode "\\.nix\\'")

(setq-default pdf-view-display-size 'fit-page)
(add-hook! 'pdf-view-mode-hook #'pdf-view-midnight-minor-mode)

(add-to-list 'display-buffer-alist
             '("\\.pdf\\'"
               (display-buffer-in-side-window)
               (side . right)
               (window-width . 0.5)
               (window-height . fit-window-to-buffer)))

(after! citar
  (setq citar-indicators nil)

  (setq citar-templates
        '((main . "${=key=:15} ${title:48} ${author editor:30%sn} ${date year issued:4}")
          (suffix . " ${=type=:12} ${tags keywords:*}")
          (preview . "${author editor:%etal} (${year issued date}) ${title}, ${journal journaltitle publisher container-title collection-title}.\n")
          (note . "Notes on ${author editor:%etal}, ${title}"))))

;; (map! :leader
;;       (:prefix ("t" . "toggle")
;;        :desc "Toggle eshell split"            "e" #'+eshell/toggle
;;        :desc "Toggle line highlight in frame" "h" #'hl-line-mode
;;        :desc "Toggle line highlight globally" "H" #'global-hl-line-mode
;;        :desc "Toggle line numbers"            "l" #'doom/toggle-line-numbers
;;        :desc "Toggle markdown-view-mode"      "m" #'dt/toggle-markdown-view-mode
;;        :desc "Toggle truncate lines"          "t" #'toggle-truncate-lines
;;        :desc "Toggle treemacs"                "T" #'+treemacs/toggle
;;        :desc "Toggle vterm split"             "v" #'+vterm/toggle))

;; (map! :leader
;;       (:prefix ("o" . "open here")
;;        :desc "Open eshell here"    "e" #'+eshell/here
;;        :desc "Open vterm here"     "v" #'+vterm/here))

;; (map! :leader
;;       :desc "M-x" "SPC" #'execute-extended-command)

;; (map! :leader
;;       (:prefix ("j" . "jupyter")
;;        :desc "Refresh kernelspecs"     "r" #'jupyter-refresh-kernelspecs
;;        :desc "Toggle raw output"       "o" (cmd! (setq +jupyter-raw-output-mode
;;                                                        (not +jupyter-raw-output-mode))
;;                                                  (message "Jupyter raw output: %s"
;;                                                           (if +jupyter-raw-output-mode "ON" "OFF")))))

;; (map! :leader
;;       (:prefix ("o" . "open")
;;         :desc "Insert template"         "t" #'+org-insert-scientific-template
;;         :desc "Toggle Python export"    "e" #'+org-toggle-python-export
;;         :desc "Set tangle file"         "f" #'+org-set-python-tangle-file
;;         :desc "Set subtree export"      "x" #'+org-set-subtree-export
;;         :desc "Insert source block"     "s" #'+org-insert-src-block))

;; (map! :leader
;;       (:prefix ("c" . "code")
;;        :desc "Format buffer"            "=" #'apheleia-format-buffer
;;        :desc "Organize imports"         "o" #'eglot-code-action-organize-imports
;;        :desc "Rename"                   "r" #'eglot-rename
;;        :desc "Find references"          "R" #'xref-find-references
;;        :desc "Show documentation"       "h" #'eldoc-doc-buffer
;;        :desc "Show doc in childframe"   "H" #'eldoc-box-help-at-point
;;        :desc "Code actions"             "a" #'eglot-code-actions
;;        :desc "Find definition"          "d" #'xref-find-definitions
;;        :desc "Find type definition"     "D" #'eglot-find-typeDefinition
;;        :desc "Go back"                  "b" #'xref-go-back))

;; (map! :leader
;;       (:prefix ("d" . "debug/dape")
;;        :desc "Debug"               "d" #'dape
;;        :desc "Toggle breakpoint"   "b" #'dape-breakpoint-toggle
;;        :desc "Continue"            "c" #'dape-continue
;;        :desc "Next"                "n" #'dape-next
;;        :desc "Step in"             "i" #'dape-step-in
;;        :desc "Step out"            "o" #'dape-step-out
;;        :desc "Restart"             "r" #'dape-restart
;;        :desc "Kill debug session"  "k" #'dape-kill
;;        :desc "Debug REPL"          "R" #'dape-repl))

(after! projectile
  ;; Ensure clean project root detection
  (setq projectile-project-root-files-bottom-up
        '(".projectile" ".git"))

  ;; Use alien indexing for better performance and reliability
  (setq projectile-indexing-method 'alien)

  ;; Ensure proper file finding
  (setq projectile-enable-caching t)

  ;; Fix potential path doubling issues
  (advice-add 'projectile-find-file :around
              (lambda (orig-fun &rest args)
                (let ((default-directory (projectile-project-root)))
                  (apply orig-fun args)))))
