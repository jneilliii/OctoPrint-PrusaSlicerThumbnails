# coding=utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import octoprint.plugin
import octoprint.filemanager
import octoprint.filemanager.util
import octoprint.util
import os
import datetime

class PrusaslicerthumbnailsPlugin(octoprint.plugin.SettingsPlugin,
                                  octoprint.plugin.AssetPlugin,
                                  octoprint.plugin.TemplatePlugin,
                                  octoprint.plugin.EventHandlerPlugin,
                                  octoprint.plugin.SimpleApiPlugin):

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
			inline_thumbnail_align_value="left",
			state_panel_thumbnail=True
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
		test_str = test_str.replace(b'\r\n',b'\n')
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
					self._file_manager.set_additional_metadata("local", payload["path"], "thumbnail_src", self._identifier, overwrite=True)

	##~~ SimpleApiPlugin mixin

	def _process_gcode(self, gcode_file, results=[]):
		self._logger.debug(gcode_file["path"])
		if gcode_file.get("type") == "machinecode":
			self._logger.debug(gcode_file.get("thumbnail"))
			if gcode_file.get("thumbnail") == None:
				self._logger.debug("No Thumbnail for %s, attempting extraction" % gcode_file["path"])
				results["no_thumbnail"].append(gcode_file["path"])
				self.on_event("FileAdded", dict(path=gcode_file["path"],storage="local",type=["gcode"]))
			elif "prusaslicerthumbnails" in gcode_file.get("thumbnail") and not gcode_file.get("thumbnail_src"):
				self._logger.debug("No Thumbnail source for %s, adding" % gcode_file["path"])
				results["no_thumbnail_src"].append(gcode_file["path"])
				self._file_manager.set_additional_metadata("local", gcode_file["path"], "thumbnail_src", self._identifier, overwrite=True)
		elif gcode_file.get("type") == "folder" and not gcode_file.get("children") == None:
			children = gcode_file["children"]
			for key, file in children.items():
				self._process_gcode(children[key], results)
		elif gcode_file.get("type") == "folder" and gcode_file.get("children") == None:
			results["warning"] = True
		return results

	def get_api_commands(self):
		return dict(crawl_files=[])

	def on_api_command(self, command, data):
		import flask
		import json
		from octoprint.server import user_permission
		if not user_permission.can():
			return flask.make_response("Insufficient rights", 403)

		if command == "crawl_files":
			self._logger.debug("Crawling Files")
			FileList = self._file_manager.list_files()
			LocalFiles = FileList["local"]
			results = dict(no_thumbnail=[],no_thumbnail_src=[])
			for key, file in LocalFiles.items():
				results = self._process_gcode(LocalFiles[key], results)
				# if LocalFiles[key].get("children") == None:
					# # self._logger.debug(LocalFiles[key].get("thumbnail"))
					# if LocalFiles[key].get("thumbnail") == None:
						# # self._logger.debug("No Thumbnail for %s, attempting extraction" % file["path"])
						# results["no_thumbnail"].append(file["path"])
						# self.on_event("FileAdded", dict(path=file["path"],storage="local",type=["gcode"]))
					# elif "prusaslicerthumbnails" in LocalFiles[key].get("thumbnail") and not LocalFiles[key].get("thumbnail_src"):
						# # self._logger.debug("No Thumbnail source for %s, adding" % file["path"])
						# results["no_thumbnail_src"].append(file["path"])
						# self._file_manager.set_additional_metadata("local", file["path"], "thumbnail_src", self._identifier, overwrite=True)
			return flask.jsonify(results)

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

