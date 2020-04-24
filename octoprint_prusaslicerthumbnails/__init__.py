# coding=utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import octoprint.plugin
import octoprint.filemanager
import octoprint.filemanager.util
import octoprint.util
import os
import datetime
from octoprint.util import to_native_str

class PrusaslicerthumbnailsPlugin(octoprint.plugin.SettingsPlugin,
                                  octoprint.plugin.AssetPlugin,
                                  octoprint.plugin.TemplatePlugin,
                                  octoprint.plugin.EventHandlerPlugin):

	def __init__(self):
		self._fileRemovalTimer = None
		self._fileRemovalLastDeleted = None
		self._fileRemovalLastAdded = None
		self._waitForAnalysis = False
		self._analysis_active = False

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			installed=True,
			inline_thumbnail=False,
			scale_inline_thumbnail=False,
			inline_thumbnail_scale_value="50",
			align_inline_thumbnail=False,
			inline_thumbnail_align_value="left"
		)

	##~~ AssetPlugin mixin

	def get_assets(self):
		return dict(
			js=["js/prusaslicerthumbnails.js"],
			css=["css/prusaslicerthumbnails.css"]
		)

	##~~ TemplatePlugin mixin

	def get_template_configs(self):
		return [
			dict(type="settings", custom_bindings=False, template="prusaslicerthumbnails_settings.jinja2"),
		]

	def _extract_thumbnail(self, gcode_filename, thumbnail_filename):
		import re
		import base64
		regex = r"(?:^; thumbnail begin \d+x\d+ \d+)(?:\n|\r\n?)((?:.+(?:\n|\r\n?))+)(?:^; thumbnail end)"
		with open(gcode_filename,"rb") as gcode_file:
			test_str = gcode_file.read().decode('utf-8')
		matches = re.findall(regex, test_str, re.MULTILINE)
		if len(matches) > 0:
			path = os.path.dirname(thumbnail_filename)
			if not os.path.exists(path):
				os.makedirs(path)
			with open(thumbnail_filename,"wb") as png_file:
				png_file.write(base64.b64decode(matches[-1:][0].replace("; ", "").encode()))

	##~~ EventHandlerPlugin mixin

	def on_event(self, event, payload):
		if event == "FolderRemoved" and payload["storage"] == "local":
			import shutil
			shutil.rmtree(self.get_plugin_data_folder() + "/" + payload["path"], ignore_errors=True)
		if event in ["FileAdded","FileRemoved"] and payload["storage"] == "local" and "gcode" in payload["type"]:
			thumbnail_filename = self.get_plugin_data_folder() + "/" + payload["path"].replace(".gcode",".png")
			if os.path.exists(thumbnail_filename):
				os.remove(thumbnail_filename)
			if event == "FileAdded":
				gcode_filename = self._file_manager.path_on_disk("local", payload["path"])
				self._extract_thumbnail(gcode_filename, thumbnail_filename)
				if os.path.exists(thumbnail_filename):
					thumbnail_url = "plugin/prusaslicerthumbnails/thumbnail/" + payload["path"].replace(".gcode", ".png") + "?" + "{:%Y%m%d%H%M%S}".format(datetime.datetime.now())
					self._file_manager.set_additional_metadata("local", payload["path"], "thumbnail", thumbnail_url, overwrite=True)

	##~~ Routes hook
	def route_hook(self, server_routes, *args, **kwargs):
		from octoprint.server.util.tornado import LargeResponseHandler, UrlProxyHandler, path_validation_factory
		from octoprint.util import is_hidden_path
		return [
				(r"thumbnail/(.*)", LargeResponseHandler, dict(path=self.get_plugin_data_folder(),
																as_attachment=False,
																path_validation=path_validation_factory(lambda path: not is_hidden_path(path),status_code=404)))
				]

	##~~ Softwareupdate hook

	def get_update_information(self):
		return dict(
			prusaslicerthumbnails=dict(
				displayName="PrusaSlicer Thumbnails",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="jneilliii",
				repo="OctoPrint-PrusaSlicerThumbnails",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/jneilliii/OctoPrint-PrusaSlicerThumbnails/archive/{target_version}.zip"
			)
		)

__plugin_name__ = "PrusaSlicer Thumbnails"
__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = PrusaslicerthumbnailsPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
		"octoprint.server.http.routes": __plugin_implementation__.route_hook
	}

