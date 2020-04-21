/*
 * View model for OctoPrint-PrusaSlicerThumbnails
 *
 * Author: jneilliii
 * License: AGPLv3
 */
$(function() {
    function PrusaslicerthumbnailsViewModel(parameters) {
        var self = this;

		self.settingsViewModel = parameters[0];
		self.filesViewModel = parameters[1];

		self.thumbnail_url = ko.observable('/static/img/tentacle-20x20.png');
		self.thumbnail_title = ko.observable('');
		self.inline_thumbnail = ko.observable();

		self.filesViewModel.open_thumbnail = function(data) {
			console.log(data);
			if(data.name.indexOf('.gcode') > 0){
				var thumbnail_title = data.path;
				var thumbnail_url = '/plugin/prusaslicerthumbnails/thumbnail/' + data.path.replace('.gcode','.png');
				self.thumbnail_url(thumbnail_url);
				self.thumbnail_title(thumbnail_title);
				$('div#prusa_thumbnail_viewer').modal("show");
			}
		}

		self.filesViewModel.inline_thumbnail_url = function(data) {
			return '/plugin/prusaslicerthumbnails/thumbnail/' + data.path.replace('.gcode','.png');
		}

		self.DEFAULT_THUMBNAIL_SCALE = "100%"
		self.filesViewModel.thumbnailScaleValue = ko.observable(self.DEFAULT_THUMBNAIL_SCALE)

		self.DEFAULT_THUMBNAIL_ALIGN = "left"
		self.filesViewModel.thumbnailAlignValue = ko.observable(self.DEFAULT_THUMBNAIL_ALIGN)

		self.onBeforeBinding = function() {
			// assign initial scaling
			if (self.settingsViewModel.settings.plugins.prusaslicerthumbnails.scale_inline_thumbnail()==true){
				self.filesViewModel.thumbnailScaleValue(self.settingsViewModel.settings.plugins.prusaslicerthumbnails.inline_thumbnail_scale_value() + "%");
			}

			// assign initial alignment
			if (self.settingsViewModel.settings.plugins.prusaslicerthumbnails.align_inline_thumbnail()==true){
				self.filesViewModel.thumbnailAlignValue(self.settingsViewModel.settings.plugins.prusaslicerthumbnails.inline_thumbnail_align_value());
			}

			// observe scaling changes
			self.settingsViewModel.settings.plugins.prusaslicerthumbnails.scale_inline_thumbnail.subscribe(function(newValue){
				if (newValue == false){
					self.filesViewModel.thumbnailScaleValue(self.DEFAULT_THUMBNAIL_SCALE);
				} else {
					self.filesViewModel.thumbnailScaleValue(self.settingsViewModel.settings.plugins.prusaslicerthumbnails.inline_thumbnail_scale_value() + "%");
				}
			});
			self.settingsViewModel.settings.plugins.prusaslicerthumbnails.inline_thumbnail_scale_value.subscribe(function(newValue){
				self.filesViewModel.thumbnailScaleValue(newValue + "%");
			});

			// observe alignment changes
			self.settingsViewModel.settings.plugins.prusaslicerthumbnails.align_inline_thumbnail.subscribe(function(newValue){
				if (newValue == false){
					self.filesViewModel.thumbnailAlignValue(self.DEFAULT_THUMBNAIL_SCALE);
				} else {
					self.filesViewModel.thumbnailAlignValue(self.settingsViewModel.settings.plugins.prusaslicerthumbnails.inline_thumbnail_align_value());
				}
			});
			self.settingsViewModel.settings.plugins.prusaslicerthumbnails.inline_thumbnail_align_value.subscribe(function(newValue){
				self.filesViewModel.thumbnailAlignValue(newValue);
			});
		}


		$(document).ready(function(){
			let regex = /<div class="btn-group action-buttons">([\s\S]*)<.div>/mi;
			let template = '<div class="btn btn-mini" data-bind="click: function() { if ($root.loginState.isUser()) { $root.open_thumbnail($data) } else { return; } }, visible: ($data.name.indexOf(\'.gcode\') > -1 && $root.settingsViewModel.settings.plugins.prusaslicerthumbnails.inline_thumbnail() == false)" title="Show Thumbnail" style="display: none;"><i class="fa fa-image"></i></div>';
			let inline_thumbnail_template = '<div class="row-fluid inline_prusa_thumbnail" ' +
			                                'data-bind="if: ($data.name.indexOf(\'.gcode\') > -1 && $root.settingsViewModel.settings.plugins.prusaslicerthumbnails.inline_thumbnail() == true), style: {\'text-align\': $root.thumbnailAlignValue}">' +
			                                '<img data-bind="attr: {src: $root.inline_thumbnail_url($data), width: $root.thumbnailScaleValue}, ' +
			                                'visible: ($data.name.indexOf(\'.gcode\') > -1 && $root.settingsViewModel.settings.plugins.prusaslicerthumbnails.inline_thumbnail() == true), ' +
			                                'click: function() { if ($root.loginState.isUser()) { $root.open_thumbnail($data) } else { return; } }" ' +
//			                                'width="100%" ' +
			                                'style="display: none;"/></div>'

			$("#files_template_machinecode").text(function () {
				var return_value = inline_thumbnail_template + $(this).text();
				return_value = return_value.replace(regex, '<div class="btn-group action-buttons">$1	' + template + '></div>');
				return return_value
			});
		});
	}

	OCTOPRINT_VIEWMODELS.push({
		construct: PrusaslicerthumbnailsViewModel,
		dependencies: ['settingsViewModel', 'filesViewModel'],
		elements: ['div#prusa_thumbnail_viewer']
	});
});
