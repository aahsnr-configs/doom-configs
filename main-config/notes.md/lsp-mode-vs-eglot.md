The short answer is **no, Eglot is no longer inherently faster than a properly tuned `lsp-mode`.**

As of mid-2026, the real-world performance delta between the two has completely leveled out. Historically, Eglot felt much faster out of the box because it is purely minimal, whereas `lsp-mode` ships with a visually heavy default setup (`lsp-ui`, breadcrumbs, sidelines, and doc child-frames) that chokes Emacs’ single-threaded UI loop.

When you strip `lsp-mode` down to replicate Eglot’s bare-bones footprint, their core execution speeds are practically identical. This convergence is largely driven by core Emacs updates and how both packages handle high-throughput server data today.

---

## Real-World User Consensus & Testimonials

Community discussions across `r/emacs` and GitHub reveal a highly nuanced picture of how these two clients perform under production pressure.

### 1. The Emacs 30 Native JSON Equalizer

For years, the biggest bottleneck for both clients was parsing massive JSON payloads from verbose language servers like `rust-analyzer` or `gopls`.

> **The Reality:** With Emacs 30's highly optimized native JSON parsing engine now standard, the performance overhead of serialization has plummeted. Actual users note that neither client induces the multi-second "completion freezes" that used to plague them on mid-sized codebases.

### 2. Keystroke Throttling & Server Choking

One area where users note Eglot feels smoother without configuration is how it handles rapid typing.

* **Eglot's approach:** It natively implements a smart debouncing mechanism. If you are typing furiously, it intelligently defers sending `didChange` notifications to the LSP server until you pause. This keeps the language server from getting overwhelmed.
* **lsp-mode's approach:** By default, it can be hyper-eager, firing off requests that back up the process pipe. However, users who apply `lsp-mode` performance tuning variables (like setting high idle delays and maximizing read-process output limits) report identical fluidity.

### 3. The Multi-Server Performance Paradox (Web Dev)

If you work in web development (e.g., TypeScript + Tailwind + ESLint), user testimonials heavily favor `lsp-mode` for performance.

* **Eglot** strictly limits buffers to a single LSP server. To use multiple, you have to route them through an external tool like `lsp-proxy`, which adds architectural overhead and configuration headache.
* **lsp-mode** handles multi-folder and multi-server architecture natively. Users working in large polyglot codebases find `lsp-mode` actually provides a *snappier* project-wide navigation experience because its virtual workspace management is highly optimized.

### 4. The `emacs-lsp-booster` Equalizer

For mega-codebases where even native JSON parsing fails to eliminate stuttering, the community doesn't debate Eglot vs. `lsp-mode` anymore. Instead, they use **`emacs-lsp-booster`** (a standalone Rust wrapper that pre-parses LSP data into bytecode before it hits Emacs). Users running both `eglot + eglot-booster` and `lsp-mode + performance flags` describe the experience as "instantaneous and indistinguishable."

---

## Performance Profiles at a Glance

| Factor | Eglot | `lsp-mode` (Stripped Down) |
| --- | --- | --- |
| **Out-of-the-box UI Overhead** | Extremely Low (Uses native `Flymake`/`ElDoc`) | High (Requires turning off `lsp-ui`, sideline, etc.) |
| **Typing Latency** | Excellent (Native request debouncing) | Excellent (Only if `lsp-idle-delay` is tuned) |
| **Memory Footprint** | Low and static | Low (Once extraneous modules are disabled) |
| **Polyglot Monorepos** | Can stutter; requires structural workarounds | Highly optimized native workspace management |

If you have already invested the effort into configuring a lightweight `lsp-mode`, **switching to Eglot purely for a speed boost will yield zero noticeable real-world gains.** The choice now boils down to philosophy: do you want a client that relies entirely on Emacs built-ins (Eglot), or do you want a feature-rich workspace coordinator that you dial back manually (`lsp-mode`)?
