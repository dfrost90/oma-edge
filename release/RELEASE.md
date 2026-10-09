# Oma Edge 0.1.9

Fixes the window-title exposure reported during marketplace review of 0.1.8.
Saving profiles and toggling Oma Edge now send JSON to the Python helper over
stdin instead of command-line arguments. The helper command line contains no
profile data. Stdin input is limited to 1 MB; malformed JSON errors do not echo
private input. Legacy CLI JSON arguments remain available for non-sensitive
requests; use `request-stdin` for private payloads.

Includes the 0.1.8 minimum-width and empty-profile fixes. Existing profiles
require no migration. Update the plugin and run `omarchy restart shell`.
First-time installations still require explicit manual setup.

Validation: 44 Python tests, Node panel tests, Lua bridge and syntax checks,
and Omarchy manifest validation pass. A subprocess test inspects actual
`/proc/<pid>/cmdline` while a private Unicode title travels over stdin and
round-trips through a temporary Unix socket. Panel tests exercise the actual
sender and startup handler. Desktop clicking was not automated for this patch.
