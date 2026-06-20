{
  description = "doom-stitcher: vanilla Emacs → literate Doom Emacs translator (Nix-managed, Python 3.13 + PGO + LTO)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };

        python = pkgs.python313.override {
          enableOptimizations = true;
          enableLTO = true;
          reproducibleBuild = false;
          self = python;
        };

        workflowDeps = python.withPackages (ps: with ps; [
          pydantic
          pydantic-ai-slim
          langgraph
          langchain-core
          openai
          httpx
          pyyaml
          rich
          tenacity
          loguru
          platformdirs
          litellm
        ]);

        # dotenvx is not packaged in nixpkgs as of this writing, so we pin
        # and shim it via `npx`. This is the *only* thing that touches
        # `.env`: it decrypts the dotenvx-encrypted secrets (using
        # `.env.keys` / $DOTENV_PRIVATE_KEY, which must exist alongside
        # `.env` but is intentionally NOT part of this flake) and injects
        # the plaintext values into the environment of whatever command it
        # wraps. Every app below runs through this wrapper so LITELLM_*,
        # GOOG_*, REDIS_*, DOOM_STITCHER_MODEL_*, DOOMDIR, etc. are all
        # available -- nothing else in this repo parses `.env` itself.
        dotenvx = pkgs.writeShellScriptBin "dotenvx" ''
          exec ${pkgs.nodejs_22}/bin/npx --yes @dotenvx/dotenvx@1.71.2 "$@"
        '';

        # Shared initialization logic between devShell and running apps.
        # Guarantees identical paths and configurations everywhere.
        shellInit = ''
          export DOOMDIR="''${DOOMDIR:-$PWD}"
          export WORKFLOW_DIR="$DOOMDIR/workflow"
          export PYTHONUNBUFFERED=1
          export PYTHONPATH="$WORKFLOW_DIR''${PYTHONPATH:+:$PYTHONPATH}"
          export SSL_CERT_FILE="${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
        '';

      in {
        # ════════════════════════════════════════════════════════════════════
        # DEVELOPMENT ENVIRONMENT (nix develop)
        # ════════════════════════════════════════════════════════════════════
        devShells.default = pkgs.mkShell {
          name = "doom-stitcher";

          packages = [
            workflowDeps
            dotenvx
            pkgs.process-compose
            pkgs.cacert
            pkgs.redis
            pkgs.pyrefly
            pkgs.ruff
            pkgs.litellm
          ];

          shellHook = ''
            # Inject standardized environment variables
            ${shellInit}

            # Minimal startup sanity checks
            echo "===================================================================="
            echo "⚡ Entering development environment for doom-stitcher ⚡"
            echo "===================================================================="
            echo "🔍 Environment verification:"
            echo "    Python:       $(python --version 2>&1)"

            # Fetch compiler flag metadata precisely matching user flags
            PGO_STATUS=$(python -c "import sysconfig; print('-fprofile-use' in (sysconfig.get_config_var('PY_CFLAGS') + sysconfig.get_config_var('PY_CFLAGS_NODIST')))")
            LTO_STATUS=$(python -c "import sysconfig; print('-flto' in (sysconfig.get_config_var('PY_CFLAGS') + sysconfig.get_config_var('PY_CFLAGS_NODIST')))")

            echo "    PGO Flag Check: $PGO_STATUS"
            echo "    LTO Flag Check: $LTO_STATUS"
            echo "--------------------------------------------------------------------"
            if [ ! -f "$DOOMDIR/.env.keys" ] && [ -z "''${DOTENV_PRIVATE_KEY:-}" ]; then
              echo "⚠️  No $DOOMDIR/.env.keys and \$DOTENV_PRIVATE_KEY is unset."
              echo "    'nix run' will fail to decrypt .env until you add one."
            fi
            echo "💡 Run 'nix run' to start the entire process-compose pipeline."
            echo "💡 Run 'nix run .#workflow' to only invoke the Python script."
            echo "💡 Run 'nix run .#litellm' to only run the LiteLLM server."
            echo "💡 For an ad-hoc shell with secrets decrypted: dotenvx run -f \"\$DOOMDIR/.env\" -- \$SHELL"
            echo "===================================================================="
          '';
        };

        # ════════════════════════════════════════════════════════════════════
        # RUNNABLE APPLICATIONS (nix run)
        # ════════════════════════════════════════════════════════════════════

        # Default: start LiteLLM + workflow together
        apps.default = {
          type = "app";
          program = pkgs.lib.getExe (pkgs.writeShellApplication {
            name = "doom-stitcher";
            runtimeInputs = [ pkgs.process-compose pkgs.cacert dotenvx pkgs.nodejs_22 ];
            text = ''
              set -euo pipefail
              ${shellInit}
              # --disable-dotenv: process-compose must NOT also load
              # $DOOMDIR/.env itself -- that file is dotenvx-encrypted
              # ciphertext, and process-compose's own .env loading would
              # inject the literal "encrypted:..." strings, clobbering the
              # plaintext values dotenvx just injected below.
              exec dotenvx run -f "$DOOMDIR/.env" -- \
                process-compose -f "$DOOMDIR/process-compose.yml" --disable-dotenv --tui=false up
            '';
          });
        };

        # Just the workflow (assumes LiteLLM already serving on $OPENAI_BASE_URL)
        apps.workflow = {
          type = "app";
          program = pkgs.lib.getExe (pkgs.writeShellApplication {
            name = "doom-stitcher-workflow";
            runtimeInputs = [ workflowDeps pkgs.cacert pkgs.curl dotenvx pkgs.nodejs_22 ];
            text = ''
              set -euo pipefail
              ${shellInit}

              # This app assumes a LiteLLM proxy is ALREADY running on
              # $OPENAI_BASE_URL (defaults to http://localhost:4000, same
              # default as workflow/config.py). Check that first so a
              # missing proxy fails with a clear message instead of a
              # raw connection-refused traceback from main.py.
              litellm_url="''${OPENAI_BASE_URL:-http://localhost:4000}"
              if ! curl -fsS --max-time 2 "$litellm_url/health/liveliness" >/dev/null 2>&1; then
                echo "error: no LiteLLM proxy reachable at $litellm_url" >&2
                echo "  Start one first, e.g. in another terminal: nix run .#litellm" >&2
                echo "  ...or run the full stack instead:           nix run" >&2
                exit 1
              fi

              cd "$WORKFLOW_DIR"
              exec dotenvx run -f "$DOOMDIR/.env" -- python main.py "$@"
            '';
          });
        };

        # Just the LiteLLM proxy
        apps.litellm = {
          type = "app";
          program = pkgs.lib.getExe (pkgs.writeShellApplication {
            name = "doom-stitcher-litellm";
            runtimeInputs = [ workflowDeps pkgs.cacert dotenvx pkgs.nodejs_22 ];
            text = ''
              set -euo pipefail
              ${shellInit}
              exec dotenvx run -f "$DOOMDIR/.env" -- \
                litellm \
                --config "$DOOMDIR/litellm-config.yaml" \
                --port "''${LITELLM_PORT:-4000}" \
                "$@"
            '';
          });
        };
      }
    );
}
