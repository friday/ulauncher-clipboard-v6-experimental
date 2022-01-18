import subprocess
from lib import logger, try_int, ensure_status, set_clipboard
from managers import Clipman, Clipster, CopyQ, GPaste
from ulauncher.api import Extension, ExtensionResult, ExtensionSmallResult
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction


clipboard_managers = [CopyQ, GPaste, Clipster, Clipman]
sorter = lambda m: int("{}{}".format(int(m.is_enabled()), int(m.is_running())))

def show_status(status):
    return [ExtensionResult(
        name          = status,
        icon          = 'edit-paste',
        highlightable = False
    )]

def format_entry(icon, query, entry):
    entry_list = entry.strip().split('\n')
    context = []
    pos = 0

    if query:
        line = next(l for l in entry_list if query in l.lower())
        pos = entry_list.index(line)

    if pos > 0:
        line = entry_list[pos - 1].strip()
        if line:
            context.append('...' + line)

    context.append(entry_list[pos])

    if len(entry_list) > pos + 1:
        line = entry_list[pos + 1].strip()
        if line:
            context.append(line + '...')

    return ExtensionSmallResult(
        icon     = icon,
        name     = '\n'.join(context),
        on_enter = ExtensionCustomAction(entry)
    )

def get_manager(name):
    if name == 'Auto':
        contenders = [m for m in clipboard_managers if m.can_start()]
        return sorted(contenders, key=sorter)[-1]

    for m in clipboard_managers:
        if m.name == name:
            return m


class Clipboard(Extension):
    def on_query_change(self, event):
        max_lines = try_int(self.preferences['max_lines'], 20)
        self.manager = get_manager(self.preferences['manager'])
        icon = 'edit-paste'
        query = (event.get_argument() or '').lower()

        if not ensure_status(self.manager):
            return show_status('Could not start {}. Please make sure you have it on your system and that it is not disabled.'.format(manager.name))

        try:
            history = self.manager.get_history()

        except Exception as e:
            logger.error('Failed getting clipboard history')
            logger.error(e)
            return show_status('Could not load clipboard history')

        # Filter entries if there's a query
        if query == '':
            matches = history[:max_lines]
        else:
            matches = []
            for entry in history:
                if len(matches) == max_lines:
                    break
                if query in entry.lower():
                    matches.append(entry)

        if len(matches) > 0:
            lines = 0
            results = []
            for entry in matches:
                result = format_entry(icon, query, entry)
                # Limit to max lines and compensate for the margin
                lines += max(1, (result.get_name().count('\n') + 1) * 0.85)
                if max_lines >= lines:
                    results.append(result)

            return results

        return show_status('No matches in clipboard history' if len(query) > 0 else 'Clipboard history is empty')

    def on_item_enter(self, event):
        text = event.get_data()
        copy_hook = self.preferences['copy_hook']

        # Prefer to use the clipboard managers own implementation
        if getattr(self.manager, 'add', None):
            logger.info("Adding to clipboard using clipboard manager's method")
            self.manager.add(text)
        else:
            logger.info("Adding to clipboard using fallback method")
            set_clipboard(text)

        if copy_hook:
            logger.info('Running copy hook: ' + copy_hook)
            subprocess.Popen(['sh', '-c', copy_hook])

if __name__ == '__main__':
    Clipboard().run()
