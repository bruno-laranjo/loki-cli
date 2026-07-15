# Shell tab completion

`loki-cli logs <TAB>` completes with the live list of targets from your
active Loki profile. The list is cached at
`~/.cache/loki-cli/targets.txt` for 60 seconds so repeated TABs are instant.
Completion is silent on any failure so it never breaks your prompt.

Install once per shell:

=== "bash"

    ```bash
    echo 'eval "$(_LOKI_CLI_COMPLETE=bash_source loki-cli)"' >> ~/.bashrc
    source ~/.bashrc
    ```

=== "zsh"

    ```bash
    echo 'eval "$(_LOKI_CLI_COMPLETE=zsh_source loki-cli)"' >> ~/.zshrc
    source ~/.zshrc
    ```

=== "fish"

    ```bash
    _LOKI_CLI_COMPLETE=fish_source loki-cli > ~/.config/fish/completions/loki-cli.fish
    ```

Then try:

```bash
loki-cli logs <TAB><TAB>       # lists all targets
loki-cli logs my-host<TAB>     # completes the unique match
```

All subcommands, options, and choice values also get completion for free —
Click handles those without a network round-trip.
