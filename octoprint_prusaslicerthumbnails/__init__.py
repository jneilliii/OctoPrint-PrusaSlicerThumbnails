# coding=utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import flask
import octoprint.plugin
import octoprint.filemanager
import octoprint.filemanager.util
import octoprint.util
import os
import datetime
import io
from PIL import Image
import re
import base64
import imghdr

from flask_babel import gettext
from octoprint.access import ADMIN_GROUP
from octoprint.access.permissions import Permissions

try:
	from urllib import quote, unquote
except ImportError:
	from urllib.parse import quote, unquote


class PrusaslicerthumbnailsPlugin(octoprint.plugin.SettingsPlugin,
								  octoprint.plugin.AssetPlugin,
								  octoprint.plugin.TemplatePlugin,
								  octoprint.plugin.EventHandlerPlugin,
								  octoprint.plugin.SimpleApiPlugin):

	def __init__(self):
		self.file_scanner = None
		self.syncing = False
		self._fileRemovalTimer = None
		self._fileRemovalLastDeleted = None
		self._fileRemovalLastAdded = None
		self._folderRemovalTimer = None
		self._folderRemovalLastDeleted = {}
		self._folderRemovalLastAdded = {}
		self._waitForAnalysis = False
		self._analysis_active = False
		self.regex_extension = re.compile("\.(?:gco(?:de)?|tft)$")

	# ~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return {'installed': True, 'inline_thumbnail': False, 'scale_inline_thumbnail': False,
				'inline_thumbnail_scale_value': "50", 'inline_thumbnail_position_left': False,
				'align_inline_thumbnail': False, 'inline_thumbnail_align_value': "left", 'state_panel_thumbnail': True,
				'state_panel_thumbnail_scale_value': "100", 'resize_filelist': False, 'filelist_height': "306",
				'scale_inline_thumbnail_position': False, 'sync_on_refresh': False, 'use_uploads_folder': False,
				'relocate_progress': False}

	# ~~ AssetPlugin mixin

	def get_assets(self):
		return {'js': ["js/prusaslicerthumbnails.js"], 'css': ["css/prusaslicerthumbnails.css"]}

	# ~~ TemplatePlugin mixin

	def get_template_configs(self):
		return [
			{'type': "settings", 'custom_bindings': False, 'template': "prusaslicerthumbnails_settings.jinja2"},
		]

	def _extract_thumbnail(self, gcode_filename, thumbnail_filename):
		regex = r"(?:^; thumbnail(?:_JPG)* begin \d+[x ]\d+ \d+)(?:\n|\r\n?)((?:.+(?:\n|\r\n?))+?)(?:^; thumbnail(?:_JPG)* end)"
		regex_mks = re.compile('(?:;(?:simage|;gimage):).*?M10086 ;[\r\n]', re.DOTALL)
		regex_weedo = re.compile('W221[\r\n](.*)[\r\n]W222', re.DOTALL)
		regex_luban = re.compile(';[Tt]humbnail: ?data:image/png;base64,(.*)[\r\n]', re.DOTALL)
		regex_qidi = re.compile('M4010.*\'(.*)\'', re.DOTALL)
		regex_creality = r"(?:^; jpg begin .*)(?:\n|\r\n?)((?:.+(?:\n|\r\n?))+?)(?:^; jpg end)"
		regex_buddy = r"(?:^; thumbnail(?:_QOI)* begin \d+[x ]\d+ \d+)(?:\n|\r\n?)((?:.+(?:\n|\r\n?))+?)(?:^; thumbnail(?:_QOI)* end)"
		lineNum = 0
		collectedString = ""
		use_mks = False
		use_weedo = False
		use_qidi = False
		use_flashprint = False
		use_creality = False
		use_buddy = False
		with open(gcode_filename, "rb") as gcode_file:
			for line in gcode_file:
				lineNum += 1
				line = line.decode("utf-8", "ignore")
				gcode = octoprint.util.comm.gcode_command_for_cmd(line)
				extrusion_match = octoprint.util.comm.regexes_parameters["floatE"].search(line)
				if gcode == "G1" and extrusion_match:
					self._logger.debug("Line %d: Detected first extrusion. Read complete.", lineNum)
					break
				if line.startswith(";") or line.startswith("\n") or line.startswith("M10086 ;") or line[0:4] in ["W220", "W221", "W222"]:
					collectedString += line
			self._logger.debug(collectedString)
			test_str = collectedString.replace(octoprint.util.to_unicode('\r\n'), octoprint.util.to_unicode('\n'))
		test_str = test_str.replace(octoprint.util.to_unicode(';\n;\n'), octoprint.util.to_unicode(';\n\n;\n'))
		matches = re.findall(regex, test_str, re.MULTILINE)
		if len(matches) == 0:  # MKS lottmaxx fallback
			matches = regex_mks.findall(test_str)
			if len(matches) > 0:
				self._logger.debug("Found mks thumbnail.")
				use_mks = True
		if len(matches) == 0:  # Weedo fallback
			matches = regex_weedo.findall(test_str)
			if len(matches) > 0:
				self._logger.debug("Found weedo thumbnail.")
				use_weedo = True
		if len(matches) == 0:  # luban fallback
			matches = regex_luban.findall(test_str)
			if len(matches) > 0:
				self._logger.debug("Found luban thumbnail.")
		if len(matches) == 0:  # Qidi fallback
			matches = regex_qidi.findall(test_str)
			if len(matches) > 0:
				self._logger.debug("Found qidi thumbnail.")
				use_qidi = True
		if len(matches) == 0:  # FlashPrint fallback
			with open(gcode_filename, "rb") as gcode_file:
				gcode_file.seek(58)
				thumbbytes = gcode_file.read(14454)
				if imghdr.what(file=None, h=thumbbytes) == 'bmp':
					self._logger.debug("Found flashprint thumbnail.")
					matches = [thumbbytes]
					use_flashprint = True
		if len(matches) == 0:  # Creality Neo fallback
			matches = re.findall(regex_creality, test_str, re.MULTILINE)
			if len(matches) > 0:
				self._logger.debug("Found creality thumbnail.")
				use_creality = True
		if len(matches) == 0: # Prusa buddy fallback
			matches = re.findall(regex_buddy, test_str, re.MULTILINE)
			if len(matches) > 0:
				self._logger.debug("Found Prusa Buddy QOI thumbnail.")
				use_buddy = True
		if len(matches) > 0:
			maxlen=0
			choosen=-1
			for i in range(len(matches)):
				curlen=len(matches[i])
				if maxlen<curlen:
					maxlen=curlen
					choosen=i
			path = os.path.dirname(thumbnail_filename)
			if not os.path.exists(path):
				os.makedirs(path)
			with open(thumbnail_filename, "wb") as png_file:
				if use_mks:
					png_file.write(self._extract_mks_thumbnail(matches))
				elif use_weedo:
					png_file.write(self._extract_weedo_thumbnail(matches))
				elif use_creality:
					png_file.write(self._extract_creality_thumbnail(matches[choosen]))
				elif use_qidi:
					self._logger.debug(matches)
				elif use_flashprint:
					png_file.write(self._extract_flashprint_thumbnail(matches))
				elif use_buddy:
					png_file.write(self._extract_buddy_thumbnail(matches[choosen].replace("; ", "")))
				else:
					png_file.write(base64.b64decode(matches[choosen].replace("; ", "").encode()))

	# Extracts a thumbnail from QOI embedded image in new Prusa Firmware
	def _extract_buddy_thumbnail(self, match):
		encoded_image = base64.b64decode(match)
		image = Image.open(io.BytesIO(encoded_image), formats=["QOI"])
		return self._imageToPng(image)

	# Extracts a thumbnail from hex binary data usd by FlashPrint slicer
	def _extract_flashprint_thumbnail(self, gcode_encoded_images):
		encoded_image = gcode_encoded_images[0]

		image = Image.open(io.BytesIO(encoded_image)).resize((160,120))
		rgba = image.convert("RGBA")
		pixels = rgba.getdata()
		newData = []

		alphamaxvalue = 35
		for pixel in pixels:
			if pixel[0] >= 0 and pixel[0] <= alphamaxvalue and pixel[1] >= 0 and  pixel[1] <= alphamaxvalue  and pixel[2] >= 0 and pixel[2] <= alphamaxvalue :  # finding black colour by its RGB value
				newData.append((255, 255, 255, 0))	# storing a transparent value when we find a black/dark colour
			else:
				newData.append(pixel)  # other colours remain unchanged

		rgba.putdata(newData)

		with io.BytesIO() as png_bytes:
			rgba.save(png_bytes, "PNG")
			png_bytes_string = png_bytes.getvalue()
		return png_bytes_string

	# Extracts a thumbnail from hex binary data usd by Qidi slicer
	def _extract_qidi_thumbnail(self, gcode_encoded_images):
		encoded_image = gcode_encoded_images[0].replace('W220 ', '').replace('\n', '').replace('\r', '').replace(' ', '')
		encoded_image = bytes(bytearray.fromhex(encoded_image))
		return encoded_image

	# Extracts a thumbnail from hex binary data usd by Weedo printers
	def _extract_weedo_thumbnail(self, gcode_encoded_images):
		encoded_image = gcode_encoded_images[0].replace('W220 ', '').replace('\n', '').replace('\r', '').replace(' ', '')
		encoded_image = bytes(bytearray.fromhex(encoded_image))
		return encoded_image

	# Extracts a thumbnail from a gcode and returns png binary string
	def _extract_mks_thumbnail(self, gcode_encoded_images):

		# Find the biggest thumbnail
		encoded_image_dimensions, encoded_image = self.find_best_thumbnail(gcode_encoded_images)

		# Not found?
		if encoded_image is None:
			return None  # What to return? Is None ok?

		# Remove M10086 ; and whitespaces
		encoded_image = encoded_image.replace('M10086 ;', '').replace('\n', '').replace('\r', '').replace(' ', '')

		# Get bytes from hex
		encoded_image = bytes(bytearray.fromhex(encoded_image))

		# Load pixel data
		image = Image.frombytes('RGB', encoded_image_dimensions, encoded_image, 'raw', 'BGR;16', 0, 1)
		return self._imageToPng(image)

	# Extracts a thumbnail from hex binary data usd by Qidi slicer
	def _extract_creality_thumbnail(self, match):
		encoded_jpg = base64.b64decode(match.replace("; ", "").encode())
		with io.BytesIO(encoded_jpg) as jpg_bytes:
			image = Image.open(jpg_bytes)
			return self._imageToPng(image)

	def _imageToPng(self, image):
		# Save image as png
		with io.BytesIO() as png_bytes:
			image.save(png_bytes, "PNG")
			png_bytes_string = png_bytes.getvalue()

		return png_bytes_string

	# Finds the biggest thumbnail
	def find_best_thumbnail(self, gcode_encoded_images):

		# Check for gimage
		for image in gcode_encoded_images:
			if image.startswith(';;gimage:'):
				# Return size and trimmed string
				return (200, 200), image[9:]

		# Check for simage
		for image in gcode_encoded_images:
			if image.startswith(';simage:'):
				# Return size and trimmed string
				return (100, 100), image[8:]

		# Image not found
		return None

	# ~~ EventHandlerPlugin mixin

	def on_event(self, event, payload):
		if event not in ["FileAdded", "FileRemoved", "FolderRemoved", "FolderAdded"]:
			return
		if event == "FolderRemoved" and payload["storage"] == "local":
			import shutil
			shutil.rmtree(self.get_plugin_data_folder() + "/" + payload["path"], ignore_errors=True)
		if event == "FolderAdded" and payload["storage"] == "local":
			file_list = self._file_manager.list_files(path=payload["path"], recursive=True)
			local_files = file_list["local"]
			results = dict(no_thumbnail=[], no_thumbnail_src=[])
			for file_key, file in local_files.items():
				results = self._process_gcode(local_files[file_key], results)
			self._logger.debug("Scan results: {}".format(results))
		if event in ["FileAdded", "FileRemoved"] and payload["storage"] == "local" and "gcode" in payload[
			"type"] and payload.get("name", False):
			thumbnail_name = self.regex_extension.sub(".png", payload["name"])
			thumbnail_path = self.regex_extension.sub(".png", payload["path"])
			if not self._settings.get_boolean(["use_uploads_folder"]):
				thumbnail_filename = "{}/{}".format(self.get_plugin_data_folder(), thumbnail_path)
			else:
				thumbnail_filename = self._file_manager.path_on_disk("local", thumbnail_path)

			if os.path.exists(thumbnail_filename):
				os.remove(thumbnail_filename)
			if event == "FileAdded":
				gcode_filename = self._file_manager.path_on_disk("local", payload["path"])
				self._extract_thumbnail(gcode_filename, thumbnail_filename)
				if os.path.exists(thumbnail_filename):
					thumbnail_url = "plugin/prusaslicerthumbnails/thumbnail/{}?{:%Y%m%d%H%M%S}".format(thumbnail_path.replace(thumbnail_name, quote(thumbnail_name)), datetime.datetime.now())
					self._file_manager.set_additional_metadata("local", payload["path"], "thumbnail", thumbnail_url.replace("//", "/"), overwrite=True)
					self._file_manager.set_additional_metadata("local", payload["path"], "thumbnail_src", self._identifier, overwrite=True)

	# ~~ SimpleApiPlugin mixin

	def _process_gcode(self, gcode_file, results=None):
		if results is None:
			results = []
		self._logger.debug(gcode_file["path"])
		if gcode_file.get("type") == "machinecode":
			self._logger.debug(gcode_file.get("thumbnail"))
			if gcode_file.get("thumbnail") is None or not os.path.exists("{}/{}".format(self.get_plugin_data_folder(), self.regex_extension.sub(".png", gcode_file["path"]))):
				self._logger.debug("No Thumbnail for %s, attempting extraction" % gcode_file["path"])
				results["no_thumbnail"].append(gcode_file["path"])
				self.on_event("FileAdded", {'path': gcode_file["path"], 'storage': "local", 'type': ["gcode"],
											'name': gcode_file["name"]})
			elif "prusaslicerthumbnails" in gcode_file.get("thumbnail") and not gcode_file.get("thumbnail_src"):
				self._logger.debug("No Thumbnail source for %s, adding" % gcode_file["path"])
				results["no_thumbnail_src"].append(gcode_file["path"])
				self._file_manager.set_additional_metadata("local", gcode_file["path"], "thumbnail_src",
														   self._identifier, overwrite=True)
		elif gcode_file.get("type") == "folder" and not gcode_file.get("children") == None:
			children = gcode_file["children"]
			for key, file in children.items():
				self._process_gcode(children[key], results)
		return results

	def get_api_commands(self):
		return dict(crawl_files=[])

	def on_api_command(self, command, data):
		import flask
		if not Permissions.PLUGIN_PRUSASLICERTHUMBNAILS_SCAN.can():
			return flask.make_response("Insufficient rights", 403)

		if command == "crawl_files":
			return flask.jsonify(self.scan_files())

	def scan_files(self):
		self._logger.debug("Crawling Files")
		file_list = self._file_manager.list_files(recursive=True)
		self._logger.debug(file_list)
		local_files = file_list["local"]
		results = dict(no_thumbnail=[], no_thumbnail_src=[])
		for key, file in local_files.items():
			results = self._process_gcode(local_files[key], results)
		self.file_scanner = None
		return results

	# ~~ extension_tree hook
	def get_extension_tree(self, *args, **kwargs):
		return dict(
			machinecode=dict(
				gcode=["tft"]
			)
		)

	# ~~ Routes hook
	def route_hook(self, server_routes, *args, **kwargs):
		from octoprint.server.util.tornado import LargeResponseHandler, path_validation_factory
		from octoprint.util import is_hidden_path
		thumbnail_root_path = self._file_manager.path_on_disk("local", "") if self._settings.get_boolean(["use_uploads_folder"]) else self.get_plugin_data_folder()
		return [
			(r"thumbnail/(.*)", LargeResponseHandler,
			 {'path': thumbnail_root_path, 'as_attachment': False, 'path_validation': path_validation_factory(
				 lambda path: not is_hidden_path(path), status_code=404)})
		]

	# ~~ Server API Before Request Hook

	def hook_octoprint_server_api_before_request(self, *args, **kwargs):
		return [self.update_file_list]

	def update_file_list(self):
		if self._settings.get_boolean(["sync_on_refresh"]) and flask.request.path.startswith(
				'/api/files') and flask.request.method == 'GET' and not self.file_scanner:
			from threading import Thread
			self.file_scanner = Thread(target=self.scan_files, daemon=True)
			self.file_scanner.start()

	# ~~ Access Permissions Hook

	def get_additional_permissions(self, *args, **kwargs):
		return [
			{'key': "SCAN", 'name': "Scan Files", 'description': gettext("Allows access to scan files."),
			 'roles': ["admin"], 'dangerous': True, 'default_groups': [ADMIN_GROUP]}
		]

	# ~~ Softwareupdate hook

	def get_update_information(self):
		return {'prusaslicerthumbnails': {'displayName': "Slicer Thumbnails", 'displayVersion': self._plugin_version,
										  'type': "github_release", 'user': "jneilliii",
										  'repo': "OctoPrint-PrusaSlicerThumbnails", 'current': self._plugin_version,
										  'stable_branch': {'name': "Stable", 'branch': "master",
															'comittish': ["master"]}, 'prerelease_branches': [
				{'name': "Release Candidate", 'branch': "rc", 'comittish': ["rc", "master"]}
			], 'pip': "https://github.com/jneilliii/OctoPrint-PrusaSlicerThumbnails/archive/{target_version}.zip"}}

	# ~~ Backup hook

	def additional_backup_excludes(self, excludes, *args, **kwargs):
		if "uploads" in excludes:
			return ["."]
		return []


__plugin_name__ = "Slicer Thumbnails"
__plugin_pythoncompat__ = ">=2.7,<4"  # python 2 and 3


def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = PrusaslicerthumbnailsPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
		"octoprint.filemanager.extension_tree": __plugin_implementation__.get_extension_tree,
		"octoprint.server.http.routes": __plugin_implementation__.route_hook,
		"octoprint.server.api.before_request": __plugin_implementation__.hook_octoprint_server_api_before_request,
		"octoprint.access.permissions": __plugin_implementation__.get_additional_permissions,
		"octoprint.plugin.backup.additional_excludes": __plugin_implementation__.additional_backup_excludes,
	}
