# coding=utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import octoprint.plugin
import octoprint.filemanager
import octoprint.filemanager.util
import octoprint.util
import os
import datetime

class ThumbnailProcessor(octoprint.filemanager.util.LineProcessorStream):

	def __init__(self, fileBufferedReader, path, logger):
		super(ThumbnailProcessor, self).__init__(fileBufferedReader)
		self._thumbnail_data = ""
		self._collecting_data = False
		self._logger = logger
		self._path = path

	def process_line(self, origLine):
		if not len(origLine):
			return None

		isBytesLineForPy3 = type(origLine) is bytes and not (type(origLine) is str)
		line = octoprint.util.to_unicode(origLine, errors="replace")
		line = line.lstrip()

		if (len(line) != 0 and line.startswith("; thumbnail end")):
			self._collecting_data = False
			if len(self._thumbnail_data) > 0:
				if os.path.exists(self._path):
					os.remove(self._path)
				import base64
				with open(self._path, "wb") as fh:
					fh.write(base64.b64decode(self._thumbnail_data))
				self._thumbnail_data = ""

		if (len(line) != 0 and self._collecting_data == True):
			self._thumbnail_data += line.replace("; ","")

		if (len(line) != 0 and line.startswith("; thumbnail begin")):
			self._collecting_data = True

		line = origLine

		if (isBytesLineForPy3 and type(line) is str):
			# line = line.encode('utf8')
			# line = line.encode('ISO-8859-1')
			line = octoprint.util.to_bytes(line, errors="replace")
		else:
			if (isBytesLineForPy3 == False):
				# do nothing, because we don't modify the line
				if (type(line) is unicode):
					line = octoprint.util.to_native_str(line)
		return line

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

	##~~ EventHandlerPlugin mixin

	def on_event(self, event, payload):
		if event == "FileAdded" and "gcode" in payload["type"]:
			self._logger.info("File Added: %s" % payload["path"])
		if event == "FileRemoved" and "gcode" in payload["type"]:
			thumbnail_filename = self.get_plugin_data_folder() + "/" + payload["path"].replace(".gcode",".png")
			if os.path.exists(thumbnail_filename):
				os.remove(thumbnail_filename)
		if event == "MetadataAnalysisStarted" and ".gcode" in payload["path"]:
			self._analysis_active = True
		if event == "MetadataAnalysisFinished" and ".gcode" in payload["path"]:
			thumbnail_filename = self.get_plugin_data_folder() + "/" + payload["path"].replace(".gcode",".png")
			if os.path.exists(thumbnail_filename):
				thumbnail_url = "/plugin/prusaslicerthumbnails/thumbnail/" + payload["path"].replace(".gcode", ".png") + "?" + "{:%Y%m%d%H%M%S}".format(datetime.datetime.now())
				self._storage_interface = self._file_manager._storage(payload.get("origin", "local"))
				self._storage_interface.set_additional_metadata(payload.get("path"), "thumbnail", thumbnail_url, overwrite=True)
			self._analysis_active = False

	##~~ preprocessor hook

	def thumbnail_extractor(self, path, file_object, links=None, printer_profile=None, allow_overwrite=True, *args, **kwargs):
		if not octoprint.filemanager.valid_file_type(path, type="gcode"):
			return file_object

		thumbnail_filename = self.get_plugin_data_folder() + "/" + path.replace(".gcode",".png")
		return octoprint.filemanager.util.StreamWrapper(file_object.filename, ThumbnailProcessor(file_object.stream(), thumbnail_filename, self._logger))
		# return file_object

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
				displayName="Prusa Slicer Thumbnails",
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

__plugin_name__ = "Prusa Slicer Thumbnails"
__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = PrusaslicerthumbnailsPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
		"octoprint.filemanager.preprocessor": __plugin_implementation__.thumbnail_extractor,
		"octoprint.server.http.routes": __plugin_implementation__.route_hook
	}

