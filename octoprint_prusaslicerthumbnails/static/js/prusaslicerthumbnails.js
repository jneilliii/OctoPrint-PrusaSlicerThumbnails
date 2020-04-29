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
		self.printerStateViewModel = parameters[2];

		self.thumbnail_url = ko.observable('/static/img/tentacle-20x20.png');
		self.thumbnail_title = ko.observable('');
		self.inline_thumbnail = ko.observable();
		self.crawling_files = ko.observable(false);
		self.crawl_results = ko.observableArray([]);
		self.show_crawl_warning = ko.observable(false);

		self.filesViewModel.prusaslicerthumbnails_open_thumbnail = function(data) {
			if(data.name.indexOf('.gcode') > 0){
				var thumbnail_title = data.path.replace('.gcode','');
				self.thumbnail_url(data.thumbnail);
				self.thumbnail_title(thumbnail_title);
				$('div#prusa_thumbnail_viewer').modal("show");
			}
		}

		self.DEFAULT_THUMBNAIL_SCALE = "100%"
		self.filesViewModel.thumbnailScaleValue = ko.observable(self.DEFAULT_THUMBNAIL_SCALE)

		self.DEFAULT_THUMBNAIL_ALIGN = "left"
		self.filesViewModel.thumbnailAlignValue = ko.observable(self.DEFAULT_THUMBNAIL_ALIGN)

		self.crawl_files = function(){
			self.crawling_files(true);
			self.crawl_results([]);
			$.ajax({
				url: API_BASEURL + "plugin/prusaslicerthumbnails",
				type: "POST",
				dataType: "json",
				data: JSON.stringify({
					command: "crawl_files"
				}),
				contentType: "application/json; charset=UTF-8"
			}).done(function(data){
				self.show_crawl_warning(false);
				for (key in data) {
					if(data[key].length && data[key] !== 'warning'){
						self.crawl_results.push({name: ko.observable(key), files: ko.observableArray(data[key])});
					} else if(key == 'warning'){
						self.show_crawl_warning(true);
					}
				}
				console.log(data);
				if(self.crawl_results().length == 0){
					self.crawl_results.push({name: ko.observable('No convertible files found'), files: ko.observableArray([])});
				}
				self.filesViewModel.requestData({force: true});
				self.crawling_files(false);
			}).fail(function(data){
				self.crawling_files(false);
			})
		}

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

			self.printerStateViewModel.filepath.subscribe(function(data){
				if(data && typeof self.printerStateViewModel.sd() !== 'undefined'){
					OctoPrint.files.get('local',data)
						.done(function(file_data){
							if(file_data){
								if(self.settingsViewModel.settings.plugins.prusaslicerthumbnails.state_panel_thumbnail() && file_data.thumbnail && file_data.thumbnail_src == 'prusaslicerthumbnails'){
									if($('#prusalicer_state_thumbnail').length) {
										$('#prusalicer_state_thumbnail > img').attr('src', file_data.thumbnail);
									} else {
										$('#state > div > hr:nth-child(4)').after('<div id="prusalicer_state_thumbnail" class="row-fluid"><img src="'+file_data.thumbnail+'" width="100%"/>\n<hr/></div>');
									}
								} else {
									$('#prusalicer_state_thumbnail').remove();
								}
							}
						})
						.fail(function(file_data){
							console.log('Error getting file information for "'+data+'"');
						});
				}
			});
		}


		$(document).ready(function(){
			let regex = /<div class="btn-group action-buttons">([\s\S]*)<.div>/mi;
			let template = '<div class="btn btn-mini" data-bind="click: function() { if ($root.loginState.isUser()) { $root.prusaslicerthumbnails_open_thumbnail($data) } else { return; } }, visible: ($data.thumbnail_src == \'prusaslicerthumbnails\' && $root.settingsViewModel.settings.plugins.prusaslicerthumbnails.inline_thumbnail() == false)" title="Show Thumbnail" style="display: none;"><i class="fa fa-image"></i></div>';
			let inline_thumbnail_template = '<div class="row-fluid inline_prusa_thumbnail" ' +
			                                'data-bind="if: ($data.thumbnail_src == \'prusaslicerthumbnails\' && $root.settingsViewModel.settings.plugins.prusaslicerthumbnails.inline_thumbnail() == true), style: {\'text-align\': $root.thumbnailAlignValue}">' +
			                                '<img data-bind="attr: {src: $data.thumbnail, width: $root.thumbnailScaleValue}, ' +
			                                'visible: ($data.thumbnail_src == \'prusaslicerthumbnails\' && $root.settingsViewModel.settings.plugins.prusaslicerthumbnails.inline_thumbnail() == true), ' +
			                                'click: function() { if ($root.loginState.isUser()) { $root.prusaslicerthumbnails_open_thumbnail($data) } else { return; } }" ' +
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
		dependencies: ['settingsViewModel', 'filesViewModel', 'printerStateViewModel'],
		elements: ['div#prusa_thumbnail_viewer', '#crawl_files', '#crawl_files_results']
	});
});
