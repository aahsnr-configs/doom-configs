The short answer is **no**, you cannot get a 1-to-1 replacement for `lsp-treemacs` using Eglot.

`lsp-treemacs` is not just a UI package; it relies on specific data structures provided by `lsp-mode` (the heavier LSP client) that Eglot (the built-in, minimalist client) does not expose or implement.

However, you can approximate **about 70%** of the functionality using Treemacs's native features and some third-party packages.

### 1. Symbols Sidebar (Class/Function Outline)

**Yes, this is possible natively.**
You do not need a special plugin. Treemacs has a built-in "Tag View" that pulls data from Emacs's `imenu` system. Since Eglot automatically populates `imenu` with symbols from the language server, they connect automatically.

- **How to do it:**
  1. Open Treemacs.
  2. Move your cursor to the file you want to inspect.
  3. Press `TAB` (or your expand key).
  4. If the file is already open, you will see the file contents (functions/variables) listed under the file icon.
- **Limitation:** It is not as "smart" as `lsp-treemacs`. It won't group items by type (e.g., separating "Methods" from "Variables") as cleanly as the LSP-specific view does; it simply lists the `imenu` index.

**Better Alternative:**
If you want a dedicated "Symbols Sidebar" similar to the `lsp-treemacs` "Symbols" tab, install **`symbols-outline`**.

- It works with Eglot out of the box.
- It creates a sidebar purely for the outline (cleaner than jamming it into the file tree).
- Add this to your Doom `packages.el`: `(package! symbols-outline)`
- Bind it to a key like `SPC c o` to toggle the outline.

### 2. Call Hierarchy Sidebar

**No, this is not possible.**
`lsp-treemacs` builds a custom tree widget for "Incoming/Outgoing Calls" by querying the server recursively. Eglot does not support the deep hooks required to feed this data into a Treemacs buffer.

- **The Eglot Way:** You must use the standard Emacs interface.
  - Run `M-x eglot-find-typeDefinition` or standard `xref` commands.
  - There is no "tree sidebar" for this in the Eglot ecosystem yet.

### 3. Project-Wide Error List

**No, this is not possible.**
`lsp-treemacs` has a specific view that groups all errors by file in the sidebar. Eglot uses **Flymake** (built-in), which does not have a sidebar view.

- **The Eglot Way:**
  - Use **`M-x consult-flymake`** (if you use the `consult` package). This gives you a searchable list of all errors in the project, which is often faster than clicking through a tree.
  - Use **`M-x flymake-show-project-diagnostics`**. This pops up a buffer listing all errors, but it is a standard list buffer, not a sidebar tree.

### Summary Strategy

If you switch to Eglot, you must give up the "Mouse-driven IDE Sidebar" philosophy of `lsp-treemacs` in exchange for the "Search-driven" philosophy of standard Emacs.

| Feature             | lsp-treemacs (lsp-mode) | Eglot equivalent                                          |
| :------------------ | :---------------------- | :-------------------------------------------------------- |
| **Symbols Sidebar** | Dedicated Tab           | **Treemacs Tag View** (built-in) or **`symbols-outline`** |
| **Call Hierarchy**  | Tree View               | **None** (use `xref-find-references`)                     |
| **Error Tree**      | Tree View               | **`consult-flymake`** (searchable list)                   |
