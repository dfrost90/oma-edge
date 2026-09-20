#!/usr/bin/env python3
"""Release managed windows and remove Edge Strip's integration, keeping settings."""
import json
import re
from pathlib import Path

import backend
import install


def main():
    # Stop management before removing the bridge needed to release reservations.
    try:
        state = backend.request({'action': 'status'})
        config = state['config']
        config['enabled'] = False
        reply = backend.request({'action': 'save', 'config': config})
        if not reply.get('ok'):
            raise RuntimeError(reply.get('error', 'Could not release managed windows'))
    except (FileNotFoundError, ConnectionRefusedError):
        if backend.CONFIG.exists():
            config = backend.validate(json.loads(backend.CONFIG.read_text()))
            config['enabled'] = False
            backend.atomic_json(backend.CONFIG, config)
        # Recover the runtime journal even if the shell service stopped abruptly.
        controller = backend.Controller()
        controller.cleanup()
        if controller.error:
            raise RuntimeError(controller.error)
    install.run('omarchy', 'plugin', 'disable', install.ID)
    hypr = install.CFG/'hypr/hyprland.lua'
    text = hypr.read_text()
    text = re.sub(r'-- Edge Strip monitor bridge \(must precede monitor configuration\)\n[^\n]+\n\n?', '', text)
    install.write(hypr, text)
    shell = json.loads((install.CFG/'omarchy/shell.json').read_text())
    bar_id = shell.get('bar', {}).get('id', '')
    bar_file = install.CFG/'omarchy/plugins'/bar_id/'Bar.qml'
    if bar_file.is_file():
        text = bar_file.read_text()
        text = install.remove_bar_adapter(text)
        install.write(bar_file, text)
    install.run('hyprctl', 'reload')
    errors = install.run('hyprctl', 'configerrors').strip()
    if errors:
        raise RuntimeError(errors)
    install.run('omarchy', 'restart', 'shell')
    print('Oma Edge disabled and integration removed. Settings and source were kept.')
    print('Backups:', install.BACKUP)


if __name__ == '__main__':
    main()
