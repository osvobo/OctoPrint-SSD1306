# coding=utf-8
from __future__ import absolute_import

import textwrap

import octoprint.plugin
from octoprint.events import Events
from octoprint.printer import PrinterCallback

from octoprint_ssd1306oleddisplay.helpers import format_seconds, format_temp

from .SSD1306 import SSD1306


class Ssd1306_oled_displayPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.ShutdownPlugin,
    octoprint.plugin.EventHandlerPlugin,
    octoprint.printer.PrinterCallback,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.TemplatePlugin,
):

    def __init__(self):
        self.display = None

    def on_after_startup(self, *args, **kwargs):
        self._logger.info('Initializing plugin')
        self.display = SSD1306(
            width=self._settings.get(['width']),
            height=self._settings.get(['height']),
            fontsize=self._settings.get(['fontsize']),
            refresh_rate=self._settings.get(['refreshrate']),
            logger=self._logger
        )
        self.display.start()
        self._clear_display()
        self._write_line_to_display(0, 'Initialized', commit=True)
        self._printer.register_callback(self)
        self._logger.debug('Initialized.')

    def on_shutdown(self):
        self._printer.unregister_callback(self)
        self._clear_display(commit=True)
        self.display.stop()

    def on_event(self, event, payload, *args, **kwargs):
        """ Display printer status events on the first line """
        self._logger.debug('on_event: %s, %s', event, payload)
        if event == Events.ERROR:
            self._write_line_to_display(
                0, 'Error! {}'.format(payload['error']), commit=True)
        elif event == Events.PRINTER_STATE_CHANGED:
            self._write_line_to_display(0, payload['state_string'])
            if payload['state_id'] == 'OFFLINE':  # Clear printer/job messages if offline
                self._clear_display(start=1, commit=True)
        elif event == Events.SHUTDOWN:
            self._clear_display(commit=True)

    def on_printer_add_temperature(self, data):
        """ Display printer temperatures on the third line """
        self._logger.debug('on_printer_add_temperature: %s', data)
        msg = []
        for k in ['bed', 'tool0', 'tool1', 'tool2']:
            if k in data.keys():
                msg.append(format_temp(k, data[k]))
        self._write_line_to_display(2, ' '.join(msg), commit=True)

    def on_printer_send_current_data(self, data, **kwargs):
        """ Display print progress on fourth line """
        self._logger.debug('on_printer_send_current_data: %s', data)
        completion = data['progress']['completion']

        if completion is None:
            # Job complete or no job started.
            self._write_line_to_display(3, '', commit=True)
        else:
            self._write_line_to_display(3, '{}% {}'.format(
                int(completion),
                # format_seconds(data['progress']['printTime']),
                format_seconds(data['progress']['printTimeLeft']),
            ), commit=True)

    def protocol_gcode_sent_hook(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        """ Listen for gcode commands, specifically M117 (Set LCD message) on the second line """
        if (gcode is not None) and (gcode == 'M117'):
            self._logger.debug('Intercepted M117 gcode: {}'.format(cmd))
            lines = textwrap.fill(
                text=' '.join(cmd.split(' ')[1:]),
                # Each char. is 8 px. wide
                width=self._settings.get(
                    ['width'])/self._settings.get(['fontsize']),
                max_lines=1  # No. of available lines
            ).split('\n')
            self._logger.debug('Split message: "%s"', lines)
            for i in range(0, len(lines)):
                self._write_line_to_display(
                    1+i, lines[i] if i < len(lines) else '')
            self._commit_to_display()

    def get_settings_defaults(self):
        return dict(
            width=128,
            height=32,
            fontsize=8,
            refreshrate=1,
        )

    def on_settings_save(self, data):
        # Cast values to integer before save.
        for k in ('width', 'height', 'fontsize', 'refreshrate'):
            if data.get(k):
                data[k] = max(0, int(data[k]))

        # Re-initialize display with new parameters.
        self.display = SSD1306(
            width=self._settings.get(['width']),
            height=self._settings.get(['height']),
            fontsize=self._settings.get(['fontsize']),
            refresh_rate=self._settings.get(['refreshrate']),
            logger=self._logger
        )
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

    def get_template_configs(self):
        return [
            dict(type="navbar", custom_bindings=False),
            dict(type="settings", custom_bindings=False)
        ]

    # Simplify calls related to display.

    def _write_line_to_display(self, line, text, commit=False):
        """ Write line to display. """
        try:
            self.display.write_row(line, text)
            if (commit):
                self.display.commit()
        except:
            self._logger.debug('Display currently unavailable.')

    def _clear_display(self, start=0, end=None, commit=False):
        """ Clear row(s). """
        try:
            self.display.clear_rows(start, end)
            if (commit):
                self.display.commit()
        except:
            self._logger.debug('Display currently unavailable.')

    def _commit_to_display(self):
        """ Commit data to be written on screen. """
        try:
            self.display.commit()
        except:
            self._logger.debug('Display currently unavailable.')

    # ~~ Softwareupdate hook

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        return {
            "ssd1306_oled_display": {
                "displayName": self._plugin_name,
                "displayVersion": self._plugin_version,

                # version check: github repository
                "type": "github_release",
                "user": "fredrikbaberg",
                "repo": "OctoPrint-SSD1306",
                "current": self._plugin_version,

                # update method: pip
                "pip": "https://github.com/fredrikbaberg/OctoPrint-SSD1306/archive/{target_version}.zip",

                "stable_branch": {
                    "name": "Stable",
                    "branch": "main",
                    "comittish": ["main"],
                },

                "prerelease_branches": [
                    {
                        "name": "Release Candidate",
                        "branch": "rc",
                        "comittish": ["rc", "main"],
                    }
                ]
            }
        }


# Set the Python version your plugin is compatible with below. Recommended is Python 3 only for all new plugins.
# OctoPrint 1.4.0 - 1.7.x run under both Python 3 and the end-of-life Python 2.
# OctoPrint 1.8.0 onwards only supports Python 3.
__plugin_pythoncompat__ = ">=3,<4"  # Only Python 3


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = Ssd1306_oled_displayPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.gcode.sent": __plugin_implementation__.protocol_gcode_sent_hook,
    }
