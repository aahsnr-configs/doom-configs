#!/bin/bash
echo "(doom! :config literate)" >~/.config/doom/init.el
git clone --depth 1 https://github.com/doomemacs/doomemacs ~/.config/emacs
~/.config/emacs/bin/doom install
~/.config/emacs/bin/doom sync
